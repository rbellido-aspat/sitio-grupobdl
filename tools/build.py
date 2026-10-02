"""Genera el sitio estático de www.grupobdl.cl en la carpeta site/ a partir de content/site.json.

Uso:
    python tools/build.py

Los formularios de contacto del sitio WordPress original se reemplazan por enlaces
a WhatsApp (ver WHATSAPP_NUMBER).
"""
import datetime
import html
import json
import os
import re
import shutil
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
UPLOADS_CACHE = os.path.join(CONTENT, "_uploads")
SITE = os.path.join(ROOT, "site")
ASSETS = os.path.join(ROOT, "tools", "assets")

BASE_URL = "https://www.grupobdl.cl"
WHATSAPP_NUMBER = "56992433573"
WHATSAPP_DEFAULT = "Hola, vengo desde el sitio web de Grupo BDL y me gustaría recibir información."
CONTACT_PAGE = "/contacto-grupobdl/"
FOOTER_BG = "#005b71"
SOCIAL = {
    "facebook": "https://www.facebook.com/BDLDiagnostico/",
    "twitter": "https://twitter.com/GrupoBDLChile",
    "youtube": "http://www.youtube.com/BDLIngenieriayRev",
    "linkedin": "http://www.linkedin.com/company/bdl-soluciones-estructurales",
}

esc = html.escape
used_uploads = set()


def wa_link(text=WHATSAPP_DEFAULT):
    return f"https://wa.me/{WHATSAPP_NUMBER}?text={quote(text)}"


# --------------------------------------------------------------------------- URLs

def fix_urls(s):
    """Reescribe las URLs del WordPress original a rutas locales del sitio estático."""
    if not s:
        return s
    s = s.replace("https://giatec.bdl.clhttps://", "https://")
    s = re.sub(r"https?://grupobdldiag789\.blob\.core\.windows\.net/imagesgrupobdlwebenapp/", "/wp-content/uploads/", s)
    s = re.sub(r"https?://(?:cdnwebgrupobdl\.azureedge\.net)/", "/", s)
    s = re.sub(r"https?://(?:www\.)?grupobdl\.cl(?=/)", "", s)
    s = s.replace("/inicio/", "/")
    # Enlaces de contacto antiguos (formularios) -> WhatsApp
    s = re.sub(r"https?://(?:www\.|end\.)?bdl\.cl/contacto/?", wa_link(), s)
    s = s.replace('href="/contacto/"', f'href="{wa_link()}"')
    # Rutas heredadas del sitio Joomla anterior que ya no existen
    s = re.sub(r'href="/(?:articulos|revision-estructural)/[^"]*"', 'href="/blog/"', s)
    # Imagen rota alojada en un dominio externo inexistente
    s = re.sub(r'<img[^>]*fprimec\.com[^>]*/>', "", s)
    return s


def track_uploads(s):
    for m in re.finditer(r"/wp-content/uploads/([^\"'()\s>&]+)", s):
        used_uploads.add(m.group(1).split("?")[0])
    return s


def upload_source(rel):
    """Ruta del archivo en la caché de uploads (algunos nombres quedaron con codificación doble)."""
    for name in (rel, rel.encode("utf8").decode("latin1", "ignore")):
        src = os.path.join(UPLOADS_CACHE, name)
        if os.path.isfile(src):
            return src
    return None


def link_missing_docs(s):
    """Los documentos que no vienen en el respaldo se solicitan por WhatsApp."""
    def repl(m):
        rel = m.group(1)
        if upload_source(rel):
            return m.group(0)
        name = os.path.splitext(os.path.basename(rel))[0].replace("-", " ")
        return f'href="{esc(wa_link(f"Hola, quiero solicitar el documento: {name}."))}" target="_blank" rel="noopener"'
    return re.sub(r'href="/wp-content/uploads/([^"]+\.pdf)"', repl, s)


def is_contact(url):
    return bool(url) and fix_urls(url).rstrip("/") in (CONTACT_PAGE.rstrip("/"), "/contacto")


# --------------------------------------------------------------------------- wpautop

ALLBLOCKS = r"(?:table|thead|tfoot|caption|col|colgroup|tbody|tr|td|th|div|dl|dd|dt|ul|ol|li|pre|form|map|area|blockquote|address|math|style|p|h[1-6]|hr|fieldset|legend|section|article|aside|hgroup|header|footer|nav|figure|figcaption|details|menu|summary|iframe)"


def youtube_id(url):
    m = re.search(r"(?:youtu\.be/|v=|embed/)([\w-]{11})", url or "")
    return m.group(1) if m else None


def youtube_embed(url):
    vid = youtube_id(url)
    if not vid:
        return ""
    return (f'<div class="video-embed"><iframe src="https://www.youtube-nocookie.com/embed/{vid}" '
            f'title="Video de YouTube" loading="lazy" allow="accelerometer; encrypted-media; gyroscope; picture-in-picture" '
            f'allowfullscreen></iframe></div>')


def wpautop(pee):
    if not pee.strip():
        return ""
    pee = pee.replace("\r\n", "\n").replace("\r", "\n")
    pee = re.sub(r"\[embed\]\s*(\S+?)\s*\[/embed\]", lambda m: "\n\n" + youtube_embed(m.group(1)) + "\n\n", pee)
    pee = re.sub(r"(?m)^\s*(https?://(?:www\.)?(?:youtube\.com/watch\S+|youtu\.be/\S+))\s*$",
                 lambda m: "\n\n" + youtube_embed(m.group(1)) + "\n\n", pee)
    pee += "\n"
    pee = re.sub(r"<br\s*/?>\s*<br\s*/?>", "\n\n", pee)
    pee = re.sub(r"(<" + ALLBLOCKS + r"[\s/>])", r"\n\n\1", pee)
    pee = re.sub(r"(</" + ALLBLOCKS + r">)", r"\1\n\n", pee)
    pee = re.sub(r"\n\n+", "\n\n", pee)
    parts = [t for t in re.split(r"\n\s*\n", pee) if t.strip()]
    pee = "".join("<p>" + t.strip("\n") + "</p>\n" for t in parts)
    pee = re.sub(r"<p>\s*</p>", "", pee)
    pee = re.sub(r"<p>([^<]+)</(div|address|form)>", r"<p>\1</p></\2>", pee)
    pee = re.sub(r"<p>\s*(</?" + ALLBLOCKS + r"[^>]*>)\s*</p>", r"\1", pee)
    pee = re.sub(r"<p>(<li.+?)</p>", r"\1", pee)
    pee = re.sub(r"<p>\s*(</?" + ALLBLOCKS + r"[^>]*>)", r"\1", pee)
    pee = re.sub(r"(</?" + ALLBLOCKS + r"[^>]*>)\s*</p>", r"\1", pee)
    pee = re.sub(r"(?<![>\n])\n(?![<\n])", "<br>\n", pee)
    pee = re.sub(r"(</?" + ALLBLOCKS + r"[^>]*>)\s*<br>", r"\1", pee)
    pee = re.sub(r"<br>(\s*</?(?:p|li|div|dl|dd|dt|th|pre|td|ul|ol)[^>]*>)", r"\1", pee)
    pee = pee.replace("&nbsp;</p>", "</p>").replace("<p>&nbsp;</p>", "")
    return pee


def clean_post_html(s):
    s = fix_urls(s)
    s = re.sub(r"<script.*?</script>", "", s, flags=re.S | re.I)
    s = re.sub(r'\sdata-style="[^"]*"', "", s)
    s = re.sub(r'<img ', '<img loading="lazy" ', s)
    return s


# --------------------------------------------------------------------------- Elementor

def dim(v, default=None):
    if isinstance(v, dict) and v.get("size") not in (None, ""):
        return f'{v["size"]}{v.get("unit") or "px"}'
    return default


def box(v):
    """Convierte un valor de padding de Elementor en CSS."""
    if not isinstance(v, dict) or all(v.get(k) in (None, "") for k in ("top", "right", "bottom", "left")):
        return None
    u = v.get("unit") or "px"
    return " ".join(f'{v.get(k) or 0}{u}' for k in ("top", "right", "bottom", "left"))


def is_dark(color):
    m = re.match(r"#([0-9a-fA-F]{6})$", color or "")
    if not m:
        return False
    r, g, b = (int(m.group(1)[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b < 0.4


def font_css(s, prefix="typography"):
    css = []
    size = s.get(f"{prefix}_font_size")
    if isinstance(size, dict) and size.get("size") not in (None, ""):
        n, u = float(size["size"]), size.get("unit") or "px"
        if u == "px" and n > 30:
            css.append(f"font-size:clamp({max(24, n * .55):.0f}px,{n / 12:.2f}vw,{n:g}px)")
        else:
            css.append(f"font-size:{n:g}{u}")
    w = s.get(f"{prefix}_font_weight")
    if w:
        css.append(f"font-weight:{w}")
    lh = s.get(f"{prefix}_line_height")
    if isinstance(lh, dict) and lh.get("size") not in (None, ""):
        css.append(f'line-height:{lh["size"]}{lh.get("unit") if lh.get("unit") != "px" or float(lh["size"]) > 4 else ""}')
    return css


def style(css):
    css = [c for c in css if c]
    return f' style="{esc(";".join(css))}"' if css else ""


def icon_class(s, key_new="selected_icon", key_old="icon"):
    v = s.get(key_new)
    if isinstance(v, dict) and isinstance(v.get("value"), str) and v.get("value"):
        return v["value"]
    return s.get(key_old) or ""


def icon_html(cls, extra=""):
    if not cls:
        return ""
    return f'<i class="{esc(cls)}" aria-hidden="true"{extra}></i>'


def link_attrs(link, fallback_text=""):
    url = (link or {}).get("url") if isinstance(link, dict) else None
    if not url:
        return None
    url = fix_urls(url)
    if url.startswith("telf:"):
        url = "tel:" + url[5:]
    attrs = f'href="{esc(url)}"'
    if url.startswith("http") and "grupobdl.cl" not in url:
        attrs += ' target="_blank" rel="noopener"'
    return attrs


class Renderer:
    def __init__(self, page_title=""):
        self.page_title = page_title

    # ---- estructura
    def render(self, elements, top=True):
        out = []
        for el in elements or []:
            if top and self.is_embedded_footer(el):
                continue
            out.append(self.element(el))
        return "\n".join(out)

    @staticmethod
    def is_embedded_footer(el):
        s = el.get("settings") or {}
        return isinstance(s, dict) and s.get("background_color") == FOOTER_BG and s.get("structure") == "70"

    def element(self, el):
        t = el.get("elType")
        if t == "section":
            return self.section(el)
        if t == "column":
            return self.column(el, 1)
        if t == "widget":
            return self.widget(el)
        return ""

    def background(self, s):
        css = []
        bg = s.get("background_background")
        if bg in ("classic", "video", "gradient"):
            if s.get("background_color"):
                css.append(f'background-color:{s["background_color"]}')
            img = (s.get("background_image") or {}).get("url")
            if img and bg != "gradient":
                img = track_uploads(fix_urls(img))
                css.append(f"background-image:url('{img}')")
                css.append(f'background-size:{s.get("background_size") or "cover"}')
                if s.get("background_size") == "auto" and not s.get("background_position"):
                    css[-1] = "background-size:contain"
                    css.append("background-position:left center")
                else:
                    css.append(f'background-position:{s.get("background_position") or "center center"}')
                css.append(f'background-repeat:{s.get("background_repeat") or "no-repeat"}')
                if s.get("background_attachment") == "fixed":
                    css.append("background-attachment:fixed")
        return css

    def overlay(self, s):
        kind = s.get("background_overlay_background")
        if kind not in ("classic", "gradient"):
            return ""
        a = s.get("background_overlay_color") or ""
        op = (s.get("background_overlay_opacity") or {}).get("size", 0.5)
        if kind == "classic":
            if not a and not (s.get("background_overlay_image") or {}).get("url"):
                return ""
            css = f"background-color:{a or 'transparent'}"
        else:
            b = s.get("background_overlay_color_b") or "transparent"
            angle = (s.get("background_overlay_gradient_angle") or {}).get("size", 180)
            sa = (s.get("background_overlay_color_stop") or {}).get("size", 0)
            sb = (s.get("background_overlay_color_b_stop") or {}).get("size", 100)
            if s.get("background_overlay_gradient_type") == "radial":
                css = f"background-image:radial-gradient(at center center,{a or 'transparent'} {sa}%,{b} {sb}%)"
            else:
                css = f"background-image:linear-gradient({angle}deg,{a or 'transparent'} {sa}%,{b} {sb}%)"
        return f'<div class="el-overlay" style="{esc(css)};opacity:{op}"></div>'

    def section(self, el):
        s = el.get("settings") or {}
        s = s if isinstance(s, dict) else {}
        inner = el.get("isInner", False)
        css = self.background(s)
        pad = box(s.get("padding"))
        if pad:
            css.append(f"padding:{pad}")
        if s.get("height") == "min-height" and not inner:
            h = s.get("custom_height") or {}
            if h.get("size"):
                unit = h.get("unit") or "px"
                size = float(h["size"])
                css.append(f"min-height:min({min(size, 100):g}vh,900px)" if unit == "vh" else f"min-height:{size:g}{unit}")
        if s.get("color_text"):
            css.append(f'color:{s["color_text"]}')
        if s.get("text_align"):
            css.append(f'text-align:{s["text_align"]}')
        shadow = s.get("box_shadow_box_shadow")
        if s.get("box_shadow_box_shadow_type") == "yes" and isinstance(shadow, dict):
            css.append(f'box-shadow:{shadow.get("horizontal", 0)}px {shadow.get("vertical", 0)}px {shadow.get("blur", 10)}px {shadow.get("spread", 0)}px {shadow.get("color", "rgba(0,0,0,.5)")}')
        cls = ["el-section", "el-inner" if inner else "el-top"]
        if is_dark(s.get("background_color")) and not s.get("color_text"):
            cls.append("on-dark")
        pos = s.get("content_position") or s.get("column_position_inner") or s.get("column_position")
        if pos in ("middle", "center"):
            cls.append("v-middle")
        elif pos == "bottom":
            cls.append("v-bottom")
        if s.get("gap") == "no":
            cls.append("gap-no")
        if s.get("height") == "min-height":
            cls.append("is-tall")
        width = None
        if s.get("layout") != "full_width" or s.get("content_width"):
            width = dim(s.get("content_width"), None if s.get("layout") == "full_width" else "1140px")
        cols = [c for c in el.get("elements", []) if c.get("elType") == "column"]
        n = max(len(cols), 1)
        body = "".join(self.column(c, n) for c in cols)
        cstyle = f' style="max-width:{width}"' if width else ""
        return (f'<section class="{" ".join(cls)}"{style(css)}>{self.overlay(s)}'
                f'<div class="el-container"{cstyle}>{body}</div></section>')

    def column(self, el, n):
        s = el.get("settings") or {}
        s = s if isinstance(s, dict) else {}
        size = s.get("_inline_size") or s.get("_column_size") or (100 / n)
        css = [f"--w:{float(size):.3f}%"]
        css += self.background(s)
        pad = box(s.get("padding"))
        inner_css = [f"padding:{pad}"] if pad else []
        pos = s.get("content_position")
        cls = "el-col" + (" v-middle" if pos in ("center", "middle") else "")
        body = "".join(self.element(c) for c in el.get("elements", []))
        return f'<div class="{cls}"{style(css)}>{self.overlay(s)}<div class="el-col-inner"{style(inner_css)}>{body}</div></div>'

    # ---- widgets
    def widget(self, el):
        t = el.get("widgetType", "")
        s = el.get("settings") or {}
        s = s if isinstance(s, dict) else {}
        fn = getattr(self, "w_" + t.replace("-", "_"), None)
        if not fn:
            return ""
        out = fn(s)
        if not out:
            return ""
        css = []
        pad = box(s.get("_padding"))
        if pad:
            css.append(f"padding:{pad}")
        return f'<div class="el-widget w-{esc(t)}"{style(css)}>{out}</div>'

    def w_heading(self, s):
        tag = s.get("header_size") or "h2"
        title = fix_urls(s.get("title") or "").strip()
        if not title:
            return ""
        title = title.replace("\n", "<br>")
        size_map = {"small": "15px", "medium": "19px", "large": "29px", "xl": "39px", "xxl": "59px"}
        css = []
        if s.get("title_color"):
            css.append(f'color:{s["title_color"]}')
        if s.get("align"):
            css.append(f'text-align:{s["align"]}')
        fc = font_css(s)
        if not any(c.startswith("font-size") for c in fc) and s.get("size") in size_map:
            fc.append(f'font-size:{size_map[s["size"]]}')
        css += fc
        la = link_attrs(s.get("link"))
        if la:
            if is_contact(s["link"]["url"]):
                la = f'href="{CONTACT_PAGE}"'
            title = f"<a {la}>{title}</a>"
        return f'<{tag} class="el-heading"{style(css)}>{title}</{tag}>'

    def w_text_editor(self, s):
        body = wpautop(clean_post_html(s.get("editor") or ""))
        css = []
        if s.get("text_color"):
            css.append(f'color:{s["text_color"]}')
        if s.get("align"):
            css.append(f'text-align:{s["align"]}')
        css += font_css(s)
        return f'<div class="el-text"{style(css)}>{track_uploads(body)}</div>'

    def img_tag(self, image, alt="", size=None):
        url = (image or {}).get("url") if isinstance(image, dict) else None
        if not url:
            return ""
        url = track_uploads(fix_urls(url))
        st = ' style="max-width:300px"' if size == "medium" else ""
        return f'<img src="{esc(url)}" alt="{esc(alt)}" loading="lazy"{st}>'

    def w_image(self, s):
        alt = s.get("caption") or self.page_title
        img = self.img_tag(s.get("image"), alt, s.get("image_size"))
        if not img:
            return ""
        la = link_attrs(s.get("link")) if s.get("link_to") == "custom" else None
        if la:
            img = f"<a {la}>{img}</a>"
        align = s.get("align") or "center"
        cap = f'<figcaption>{esc(s["caption"])}</figcaption>' if s.get("caption") else ""
        return f'<figure class="el-image" style="text-align:{align}">{img}{cap}</figure>'

    def w_image_box(self, s):
        title = s.get("title_text") or ""
        img = self.img_tag(s.get("image"), title or self.page_title)
        w = dim(s.get("image_size"))
        if img and w:
            img = img.replace("<img ", f'<img style="width:{w}" ', 1)
        desc = (s.get("description_text") or "").strip()
        la = link_attrs(s.get("link"))
        tcss = [f'color:{s["title_color"]}'] if s.get("title_color") else []
        dcss = [f'color:{s["description_color"]}'] if s.get("description_color") else []
        t = f"<a {la}>{esc(title)}</a>" if la and title else esc(title)
        parts = []
        if img:
            parts.append(f'<div class="ib-img">{f"<a {la}>{img}</a>" if la else img}</div>')
        body = ""
        if title:
            body += f'<h3 class="ib-title"{style(tcss)}>{t}</h3>'
        if desc:
            body += f'<p class="ib-desc"{style(dcss)}>{esc(desc).replace(chr(10), "<br>")}</p>'
        if body:
            parts.append(f'<div class="ib-content">{body}</div>')
        pos = s.get("position") or "top"
        align = s.get("text_align") or "center"
        return f'<div class="el-image-box pos-{pos}" style="text-align:{align}">{"".join(parts)}</div>'

    def w_icon_box(self, s):
        title = (s.get("title_text") or "").strip()
        desc = (s.get("description_text") or "").strip()
        la = link_attrs(s.get("link"))
        color = s.get("primary_color") or "#61ce70"
        size = dim(s.get("icon_size"), "50px")
        icon = icon_html(icon_class(s), f' style="color:{color};font-size:{size}"')
        if la:
            icon = f"<a {la}>{icon}</a>"
        tcss = [f'color:{s["title_color"]}'] if s.get("title_color") else []
        dcss = [f'color:{s["description_color"]}'] if s.get("description_color") else []
        body = ""
        if title:
            body += f'<h3 class="ib-title"{style(tcss)}>{f"<a {la}>{esc(title)}</a>" if la else esc(title)}</h3>'
        if desc:
            body += f'<p class="ib-desc"{style(dcss)}>{esc(desc)}</p>'
        pos = s.get("position") or "top"
        align = s.get("text_align") or "center"
        return f'<div class="el-icon-box pos-{pos}" style="text-align:{align}"><div class="ib-icon">{icon}</div><div class="ib-content">{body}</div></div>'

    def w_icon_list(self, s):
        items = []
        icolor = s.get("icon_color") or ""
        tcolor = s.get("text_color") or ""
        for it in s.get("icon_list") or []:
            text = esc((it.get("text") or "").strip())
            ic = icon_html(icon_class(it), f' style="color:{icolor}"' if icolor else "")
            la = link_attrs(it.get("link"))
            inner = f'<span class="il-icon">{ic}</span><span class="il-text"{style([f"color:{tcolor}"] if tcolor else [])}>{text}</span>'
            items.append(f"<li>{f'<a {la}>{inner}</a>' if la else inner}</li>")
        layout = " inline" if s.get("view") == "inline" else ""
        return f'<ul class="el-icon-list{layout}">{"".join(items)}</ul>'

    def w_button(self, s):
        text = s.get("text") or "Saber más"
        url = (s.get("link") or {}).get("url") or "#"
        to_whatsapp = is_contact(url)
        if to_whatsapp:
            href = wa_link(f"Hola, vengo desde la página {self.page_title} de Grupo BDL y quiero solicitar información.")
            attrs = f'href="{esc(href)}" target="_blank" rel="noopener"'
        else:
            attrs = link_attrs(s.get("link")) or 'href="#"'
        bg = s.get("background_color") or "#61ce70"
        fg = s.get("button_text_color") or "#ffffff"
        bgh = s.get("button_background_hover_color") or bg
        fgh = s.get("hover_color") or fg
        border = s.get("border_color") or fg
        css = f"--bg:{bg};--fg:{fg};--bgh:{bgh};--fgh:{fgh};--bd:{border}"
        transparent = "rgba(255,255,255,0)" in bg or "rgba(0,0,0,0)" in bg
        cls = "el-button" + (" outline" if transparent else "") + (f' size-{s["size"]}' if s.get("size") else "")
        icon = '<i class="fa-brands fa-whatsapp" aria-hidden="true"></i> ' if to_whatsapp else ""
        align = s.get("align") or "left"
        return f'<div class="btn-wrap" style="text-align:{align}"><a class="{cls}" style="{css}" {attrs}>{icon}{esc(text)}</a></div>'

    def w_animated_headline(self, s):
        before = esc(s.get("before_text") or "")
        after = esc(s.get("after_text") or "")
        words = [w.strip() for w in (s.get("rotating_text") or s.get("highlighted_text") or "").split("\n") if w.strip()]
        if s.get("headline_style") != "rotate":
            words = [s.get("highlighted_text") or ""]
        tcolor = s.get("title_color") or "#54595f"
        wcolor = s.get("words_color") or tcolor
        spans = "".join(f'<b class="{"is-on" if i == 0 else ""}">{esc(w)}</b>' for i, w in enumerate(words))
        css = [f"color:{tcolor}", f'text-align:{s.get("alignment") or "center"}'] + font_css(s, "title_typography")
        wcss = [f"color:{wcolor}"] + font_css(s, "words_typography")
        return (f'<h2 class="el-anim-headline"{style(css)}>{before} '
                f'<span class="rotator"{style(wcss)} aria-label="{esc(", ".join(words))}">{spans}</span> {after}</h2>')

    def w_slides(self, s):
        slides = []
        for i, sl in enumerate(s.get("slides") or []):
            img = (sl.get("background_image") or {}).get("url")
            bg = f"background-image:url('{track_uploads(fix_urls(img))}');" if img else ""
            bg += f'background-color:{sl.get("background_color") or "#ccc"}'
            la = link_attrs(sl.get("link"))
            btn = f'<a class="el-button" style="--bg:#fff;--fg:#006b6d;--bgh:#006b6d;--fgh:#fff;--bd:#fff" {la}>{esc(sl.get("button_text") or "Saber más")}</a>' if la else ""
            slides.append(
                f'<div class="slide{" is-on" if i == 0 else ""}" style="{esc(bg)}">'
                f'<div class="slide-content"><h2>{esc(sl.get("heading") or "")}</h2>'
                f'<p>{esc((sl.get("description") or "").replace(chr(8203), ""))}</p>{btn}</div></div>')
        dots = "".join(f'<button type="button" aria-label="Diapositiva {i + 1}"{" class=is-on" if i == 0 else ""}></button>' for i in range(len(slides)))
        return f'<div class="el-slides" data-slider>{"".join(slides)}<div class="dots">{dots}</div></div>'

    def w_tabs(self, s):
        heads, panes = [], []
        for i, tab in enumerate(s.get("tabs") or []):
            title = tab.get("tab_title") or f"Pestaña {i + 1}"
            content = tab.get("tab_content") or ""
            if "typeform" in content:
                # Formulario de solicitud (Typeform) reemplazado por un enlace a WhatsApp
                msg = f"Hola, vengo desde el sitio web de Grupo BDL y quiero solicitar el servicio de {title}."
                content = (f'<div class="wa-card"><p>Cuéntanos sobre tu proyecto y te respondemos directamente por WhatsApp.</p>'
                           f'<a class="wa-button" href="{esc(wa_link(msg))}" target="_blank" rel="noopener">'
                           f'<i class="fa-brands fa-whatsapp" aria-hidden="true"></i> Solicitar {esc(title)} por WhatsApp</a></div>')
            else:
                content = wpautop(clean_post_html(content))
            on = " is-on" if i == 0 else ""
            heads.append(f'<button type="button" class="tab-title{on}" data-tab="{i}" role="tab" aria-selected="{"true" if i == 0 else "false"}">{esc(title)}</button>')
            panes.append(f'<div class="tab-pane{on}" data-pane="{i}" role="tabpanel">{track_uploads(content)}</div>')
        return f'<div class="el-tabs" data-tabs><div class="tab-heads" role="tablist">{"".join(heads)}</div>{"".join(panes)}</div>'

    def w_video(self, s):
        if s.get("video_type") == "hosted":
            url = (s.get("hosted_url") or {}).get("url")
            if not url:
                return ""
            url = track_uploads(fix_urls(url))
            return f'<div class="video-embed"><video src="{esc(url)}" controls preload="metadata" playsinline></video></div>'
        return youtube_embed(s.get("youtube_url") or s.get("link") or "")

    def w_google_maps(self, s):
        address = s.get("address") or ""
        if address == "San Antonio 19":
            address = "San Antonio 19, Santiago, Chile"
        zoom = (s.get("zoom") or {}).get("size", 15)
        h = (s.get("height") or {}).get("size", 400)
        src = f"https://maps.google.com/maps?q={quote(address)}&t=m&z={zoom}&output=embed&iwloc=near"
        return f'<div class="el-map"><iframe src="{esc(src)}" style="height:{h}px" title="{esc(address)}" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe></div>'

    def w_divider(self, s):
        color = s.get("color") or "#ddd"
        weight = dim(s.get("weight"), "1px")
        st = s.get("style") or "solid"
        gap = dim(s.get("gap"), "15px")
        return f'<hr class="el-divider" style="border-top:{weight} {st} {color};margin:{gap} 0">'

    def w_social_icons(self, s):
        items = []
        for it in s.get("social_icon_list") or []:
            cls = icon_class(it, "social_icon", "social")
            if "google" in cls or "wordpress" in cls:
                cls = it.get("social") or cls
            key = next((k for k in SOCIAL if k in cls), None)
            if not key:
                continue
            url = (it.get("link") or {}).get("url") or SOCIAL[key]
            items.append(f'<a href="{esc(url)}" target="_blank" rel="noopener" aria-label="{key.title()}"><i class="fa-brands fa-{key}" aria-hidden="true"></i></a>')
        items.append(f'<a href="{esc(wa_link())}" target="_blank" rel="noopener" aria-label="WhatsApp"><i class="fa-brands fa-whatsapp" aria-hidden="true"></i></a>')
        align = s.get("align") or "center"
        return f'<div class="el-social" style="justify-content:{ {"left": "flex-start", "right": "flex-end"}.get(align, "center") }">{"".join(items)}</div>'

    def w_icon(self, s):
        color = s.get("primary_color") or "#54595f"
        ic = icon_html(icon_class(s), f' style="color:{color}"')
        return f'<div class="el-icon"><a href="#contenido" aria-label="Bajar al contenido">{ic}</a></div>'

    def w_nav_menu(self, s):
        return ""


# --------------------------------------------------------------------------- Plantillas

def nav_html(menu):
    top = [m for m in menu if m["parent"] == "0"]
    out = []
    for m in top:
        url = fix_urls(m["url"])
        if url == "/inicio/":
            url = "/"
        kids = [k for k in menu if k["parent"] == m["id"]]
        if kids:
            sub = "".join(f'<li><a href="{esc(k["url"])}" target="_blank" rel="noopener">{esc(k["title"])}</a></li>' for k in kids)
            out.append(f'<li class="has-sub"><a href="{esc(url)}">{esc(m["title"])}</a>'
                       f'<button class="sub-toggle" type="button" aria-label="Abrir submenú {esc(m["title"])}" aria-expanded="false"><i class="fa-solid fa-chevron-down" aria-hidden="true"></i></button>'
                       f'<ul class="sub">{sub}</ul></li>')
        else:
            out.append(f'<li><a href="{esc(url)}">{esc(m["title"])}</a></li>')
    return "".join(out)


def build_menu(raw):
    menu = list(raw)
    # Se agrega "Empresa", página publicada que no figuraba en el menú original
    if not any(m["url"].rstrip("/").endswith("empresa-grupobdl") for m in menu):
        menu.insert(1, {"id": "emp", "parent": "0", "title": "Empresa", "url": "/empresa-grupobdl/", "type": "post_type"})
    for m in menu:
        if m["title"] == "Home":
            m["title"] = "Inicio"
    return menu


def layout(*, title, desc, path, body, menu, footer, body_class="", og_image="/wp-content/uploads/2018/05/logo_bdl_green.png", noindex=False):
    canonical = BASE_URL + path
    year = datetime.date.today().year
    robots = '<meta name="robots" content="noindex">' if noindex else ""
    return f"""<!doctype html>
<html lang="es-CL">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{robots}
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:locale" content="es_ES">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:site_name" content="Grupo BDL">
<meta property="og:image" content="{esc(BASE_URL + og_image)}">
<link rel="icon" href="/favicon.png" type="image/png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Roboto:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=Roboto+Slab:wght@400;600&display=swap">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/v4-shims.min.css">
<link rel="stylesheet" href="/assets/styles.css">
</head>
<body class="{body_class}">
<a class="skip" href="#contenido">Saltar al contenido</a>
<header class="site-header">
  <div class="header-inner">
    <a class="logo" href="/" aria-label="Grupo BDL, inicio"><img src="/wp-content/uploads/2018/05/logo_bdl_green.png" alt="Grupo BDL" width="159" height="66"></a>
    <button class="menu-toggle" type="button" aria-label="Abrir menú" aria-expanded="false" aria-controls="menu-principal"><i class="fa-solid fa-bars" aria-hidden="true"></i></button>
    <nav class="main-nav" id="menu-principal" aria-label="Menú principal"><ul>{nav_html(menu)}</ul></nav>
  </div>
</header>
<main id="contenido">
{body}
</main>
<footer class="site-footer">
{footer}
<div class="footer-bottom"><div class="wrap">© {year} Grupo BDL · <a href="{esc(wa_link())}" target="_blank" rel="noopener">WhatsApp +56 9 9243 3573</a></div></div>
</footer>
<a class="wa-float" href="{esc(wa_link())}" target="_blank" rel="noopener" aria-label="Escríbenos por WhatsApp"><i class="fa-brands fa-whatsapp" aria-hidden="true"></i><span>Escríbenos</span></a>
<script src="/assets/main.js" defer></script>
</body>
</html>
"""


def strip_tags(s):
    s = re.sub(r"\[/?\w+[^\]]*\]", " ", s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"https?://\S+", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def excerpt(post, words=28):
    text = strip_tags(post.get("excerpt") or post["content"])
    w = text.split()
    return " ".join(w[:words]) + ("…" if len(w) > words else "")


def first_image(post):
    m = re.search(r'<img[^>]+src="([^"]+)"', fix_urls(post["content"]))
    if m and m.group(1).startswith("/wp-content/uploads/"):
        return m.group(1)
    return ""


MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def fmt_date(d):
    dt = datetime.datetime.strptime(d[:10], "%Y-%m-%d")
    return f"{dt.day} de {MONTHS[dt.month - 1]} de {dt.year}"


def write(path, text):
    full = os.path.join(SITE, path.strip("/"), "index.html") if not path.endswith(".html") else os.path.join(SITE, path.lstrip("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf8", newline="\n") as fh:
        fh.write(text)


def wa_cta(text, msg=WHATSAPP_DEFAULT, extra=""):
    return (f'<section class="cta-wa"><div class="wrap"><p>{text}</p>{extra}'
            f'<a class="wa-button" href="{esc(wa_link(msg))}" target="_blank" rel="noopener">'
            f'<i class="fa-brands fa-whatsapp" aria-hidden="true"></i> Escríbenos por WhatsApp</a></div></section>')


# --------------------------------------------------------------------------- Build

def main():
    data = json.load(open(os.path.join(CONTENT, "site.json"), encoding="utf8"))
    os.makedirs(SITE, exist_ok=True)
    for name in os.listdir(SITE):  # se vacía el contenido sin borrar la carpeta
        full = os.path.join(SITE, name)
        shutil.rmtree(full) if os.path.isdir(full) else os.remove(full)

    menu = build_menu(data["menu"])
    footer = Renderer("Grupo BDL").render(data["footer"], top=False)
    track_uploads("/wp-content/uploads/2018/05/logo_bdl_green.png")
    pages = {p["slug"]: p for p in data["pages"]}
    posts = data["posts"]
    sitemap = []

    def page(path, title, desc, body, **kw):
        write(path, layout(title=title, desc=desc, path=path, body=track_uploads(link_missing_docs(body)), menu=menu, footer=footer, **kw))
        if not kw.get("noindex"):
            sitemap.append(path)

    # Páginas construidas con Elementor
    elementor_pages = {
        "inicio": "/",
        "empresa-grupobdl": "/empresa-grupobdl/",
        "diagnostico-estructural": "/diagnostico-estructural/",
        "refuerzo-estructural": "/refuerzo-estructural/",
        "contacto-grupobdl": CONTACT_PAGE,
    }
    for slug, path in elementor_pages.items():
        p = pages[slug]
        r = Renderer(p["title"] if slug != "inicio" else "de inicio")
        body = r.render(p["elementor"])
        if slug == "contacto-grupobdl":
            # El formulario de contacto se reemplaza por WhatsApp, justo bajo la portada
            cta = wa_cta("La forma más rápida de hablar con nosotros es por WhatsApp. Cuéntanos qué necesitas y te respondemos directamente.",
                         extra='<p class="wa-number">+56 9 9243 3573</p>')
            parts = body.split("</section>", 1)
            body = parts[0] + "</section>" + cta + (parts[1] if len(parts) > 1 else "")
        elif slug != "inicio":
            cta_text = {
                "empresa-grupobdl": "¿Quieres trabajar con Grupo BDL? Conversemos sobre tu proyecto.",
                "diagnostico-estructural": "¿Necesitas un diagnóstico estructural? Conversemos sobre tu proyecto.",
                "refuerzo-estructural": "¿Necesitas reforzar una estructura? Conversemos sobre tu proyecto.",
            }[slug]
            body += wa_cta(cta_text,
                           f"Hola, vengo desde la página {p['title']} de Grupo BDL y quiero solicitar información.")
        title = p["seo_title"] or (f'{p["title"]} | Grupo BDL' if slug != "inicio" else "Grupo BDL | Ingeniería estructural, diagnóstico y refuerzo")
        desc = p["seo_desc"] or strip_tags(body)[:155]
        page(path, title, desc, body, body_class=f"page-{slug}")

    # Productos (página vacía en WordPress; sus subpáginas eran enlaces externos)
    prod_items = [m for m in menu if m["parent"] == next((x["id"] for x in menu if x["title"] == "Productos"), None)]
    cards = "".join(
        f'<a class="product-card" href="{esc(m["url"])}" target="_blank" rel="noopener"><h2>{esc(m["title"])}</h2>'
        f'<span>{esc(re.sub(r"^https?://", "", m["url"]).rstrip("/"))} <i class="fa-solid fa-arrow-up-right-from-square" aria-hidden="true"></i></span></a>'
        for m in prod_items)
    body = (f'<section class="page-hero"><div class="wrap"><h1>Productos</h1></div></section>'
            f'<section class="wrap products">{cards}</section>'
            + wa_cta("¿Quieres saber más sobre nuestros productos?", "Hola, vengo desde el sitio web de Grupo BDL y quiero información sobre sus productos."))
    page("/productos/", "Productos | Grupo BDL", "Productos distribuidos por Grupo BDL.", body, body_class="page-productos")

    # Blog
    cats = sorted({c for p in posts for c in p["categories"]})
    filt = '<div class="blog-filter" role="group" aria-label="Filtrar por categoría"><button type="button" class="is-on" data-cat="">Todos</button>' + "".join(
        f'<button type="button" data-cat="{esc(c)}">{esc(c)}</button>' for c in cats) + "</div>"
    cards = []
    for p in posts:
        img = first_image(p)
        img_html = f'<img src="{esc(img)}" alt="" loading="lazy">' if img else '<div class="card-noimg"><i class="fa-solid fa-building" aria-hidden="true"></i></div>'
        cards.append(
            f'<article class="card" data-cats="{esc("|".join(p["categories"]))}"><a href="/{esc(p["slug"])}/">'
            f'<div class="card-img">{img_html}</div><div class="card-body">'
            f'<p class="card-meta">{esc(", ".join(p["categories"]))}</p>'
            f'<h2>{esc(p["title"])}</h2><p>{esc(excerpt(p))}</p></div></a></article>')
    body = (f'<section class="page-hero"><div class="wrap"><h1>Artículos</h1>'
            f'<p>Ensayos no destructivos, diagnóstico estructural y control de calidad del hormigón.</p></div></section>'
            f'<section class="wrap">{filt}<div class="cards">{"".join(cards)}</div></section>')
    page("/blog/", "Artículos | Grupo BDL", "Artículos técnicos de Grupo BDL sobre ensayos no destructivos, diagnóstico estructural y control de calidad del hormigón.", body, body_class="page-blog")

    # Artículos
    for i, p in enumerate(posts):
        content = track_uploads(wpautop(clean_post_html(p["content"])))
        cats = ", ".join(p["categories"])
        prev_p = posts[i + 1] if i + 1 < len(posts) else None
        next_p = posts[i - 1] if i > 0 else None
        nav = '<nav class="post-nav" aria-label="Más artículos">'
        nav += f'<a href="/{esc(prev_p["slug"])}/"><span>Anterior</span>{esc(prev_p["title"])}</a>' if prev_p else "<span></span>"
        nav += f'<a class="next" href="/{esc(next_p["slug"])}/"><span>Siguiente</span>{esc(next_p["title"])}</a>' if next_p else "<span></span>"
        nav += "</nav>"
        body = (f'<article class="post"><header class="post-header"><div class="wrap narrow">'
                f'<p class="post-meta"><a href="/blog/">Artículos</a>{" · " + esc(cats) if cats else ""}</p>'
                f'<h1>{esc(p["title"])}</h1></div></header>'
                f'<div class="wrap narrow post-content">{content}</div></article>'
                + wa_cta("¿Tienes dudas sobre este tema o quieres aplicarlo en tu obra? Conversemos.",
                         f"Hola, leí el artículo \"{p['title']}\" en el sitio de Grupo BDL y quiero más información.")
                + f'<div class="wrap narrow">{nav}</div>')
        title = p["seo_title"] or f'{p["title"]} | Grupo BDL'
        desc = p["seo_desc"] or excerpt(p, 26)
        img = first_image(p)
        page(f'/{p["slug"]}/', title, desc, body, body_class="single-post", **({"og_image": img} if img else {}))

    # 404
    body = ('<section class="page-hero"><div class="wrap"><h1>Página no encontrada</h1>'
            '<p>La página que buscas no existe o cambió de dirección.</p>'
            '<p><a class="el-button" style="--bg:#16666b;--fg:#fff;--bgh:#61ce70;--fgh:#fff;--bd:#16666b" href="/">Ir al inicio</a> '
            '<a class="el-button" style="--bg:#fff;--fg:#16666b;--bgh:#16666b;--fgh:#fff;--bd:#16666b" href="/blog/">Ver artículos</a></p></div></section>'
            + wa_cta("¿No encuentras lo que buscas? Escríbenos."))
    write("/404.html", layout(title="Página no encontrada | Grupo BDL", desc="Página no encontrada", path="/404.html", body=body, menu=menu, footer=footer, noindex=True))

    # Recursos estáticos
    shutil.copytree(ASSETS, os.path.join(SITE, "assets"))
    shutil.copy(os.path.join(ASSETS, "..", "favicon.png"), os.path.join(SITE, "favicon.png"))
    shutil.copy(os.path.join(ROOT, "staticwebapp.config.json"), os.path.join(SITE, "staticwebapp.config.json"))
    missing = []
    for rel in sorted(used_uploads):
        src = upload_source(rel)
        if src:
            dst = os.path.join(SITE, "wp-content", "uploads", rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
        else:
            missing.append(rel)

    today = datetime.date.today().isoformat()
    urls = "".join(f"<url><loc>{BASE_URL}{p}</loc><lastmod>{today}</lastmod></url>" for p in sitemap)
    with open(os.path.join(SITE, "sitemap.xml"), "w", encoding="utf8") as fh:
        fh.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    with open(os.path.join(SITE, "robots.txt"), "w", encoding="utf8") as fh:
        fh.write(f"User-agent: *\nAllow: /\n\nSitemap: {BASE_URL}/sitemap.xml\n")

    print(f"{len(sitemap)} páginas generadas, {len(used_uploads) - len(missing)} imágenes copiadas")
    if missing:
        print("Archivos referenciados que no están en el respaldo:")
        for m in missing:
            print("  ", m)


if __name__ == "__main__":
    main()
