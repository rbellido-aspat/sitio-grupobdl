"""Extrae el contenido del respaldo WordPress (.wpress de All-in-One WP Migration)
de www.grupobdl.cl y lo deja en content/site.json, listo para build.py.

Uso:
    python tools/export_wpress.py "<ruta al .wpress>"

Solo lee la base de datos (database.sql) y la carpeta uploads/. No guarda
usuarios, contraseñas ni registros de Wordfence.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
UPLOADS_CACHE = os.path.join(ROOT, "content", "_uploads")  # ignorado por git

WANTED_TABLES = {"posts", "postmeta", "options", "terms", "term_taxonomy", "term_relationships"}
BS, Q = chr(92), chr(39)
ESC = {"n": "\n", "r": "\r", "t": "\t", "0": "\0", "Z": "\x1a"}

# Páginas Elementor que se publican, plantillas de cabecera y pie
HEADER_ID, FOOTER_ID = "1010", "1161"


def iter_wpress(path):
    """Recorre el .wpress devolviendo (ruta, tamaño, handle posicionado al inicio del archivo)."""
    f = open(path, "rb")
    while True:
        h = f.read(4377)
        if len(h) < 4377 or h == b"\0" * 4377:
            break
        name = h[:255].rstrip(b"\0").decode("utf8", "replace")
        size = int(h[255:269].rstrip(b"\0") or 0)
        prefix = h[281:].rstrip(b"\0").decode("utf8", "replace")
        rel = os.path.normpath(os.path.join(prefix, name)).replace("\\", "/")
        start = f.tell()
        yield rel, size, f
        f.seek(start + size)


def parse_values(s, i):
    rows = []
    n = len(s)
    while i < n:
        while s[i] in " ,\n":
            i += 1
        if s[i] == ";":
            break
        i += 1  # (
        row = []
        while True:
            c = s[i]
            if c == Q:
                i += 1
                buf = []
                while True:
                    c = s[i]
                    if c == BS:
                        nx = s[i + 1]
                        buf.append(ESC.get(nx, nx))
                        i += 2
                    elif c == Q:
                        if s[i + 1:i + 2] == Q:
                            buf.append(Q)
                            i += 2
                        else:
                            i += 1
                            break
                    else:
                        j = i
                        while s[j] != BS and s[j] != Q:
                            j += 1
                        buf.append(s[i:j])
                        i = j
                row.append("".join(buf))
            else:
                j = i
                while s[j] not in ",)":
                    j += 1
                v = s[i:j].strip()
                row.append(None if v == "NULL" else v)
                i = j
            while s[i] == " ":
                i += 1
            if s[i] == ",":
                i += 1
                continue
            if s[i] == ")":
                i += 1
                break
        rows.append(row)
    return rows


def load_tables(sql_text):
    tables = {t: [] for t in WANTED_TABLES}
    for line in sql_text.split(chr(10)):
        m = re.match(r"INSERT INTO `SERVMASK_PREFIX_(\w+)` VALUES ", line)
        if m and m.group(1) in WANTED_TABLES:
            tables[m.group(1)].extend(parse_values(line + "\n", m.end()))
    return tables


def main(wpress):
    os.makedirs(CONTENT, exist_ok=True)
    sql = None
    for rel, size, f in iter_wpress(wpress):
        if rel == "database.sql":
            sql = f.read(size).decode("utf8", "replace")
            break
    tables = load_tables(sql)

    posts = {r[0]: r for r in tables["posts"]}
    meta = {}
    for r in tables["postmeta"]:
        meta.setdefault(r[1], {})[r[2]] = r[3]
    options = {r[1]: r[2] for r in tables["options"]}
    terms = {r[0]: r[1] for r in tables["terms"]}
    tax = {r[0]: (r[1], r[2]) for r in tables["term_taxonomy"]}  # tt_id -> (term_id, taxonomy)
    rel_by_post = {}
    for r in tables["term_relationships"]:
        rel_by_post.setdefault(r[0], []).append(r[1])

    def attachment_url(att_id):
        p = posts.get(att_id)
        return p[18] if p else ""

    def elementor(pid):
        raw = meta.get(pid, {}).get("_elementor_data")
        return json.loads(raw) if raw else None

    out = {
        "site": {"name": options.get("blogname", "Grupo BDL"), "url": "https://www.grupobdl.cl"},
        "header": elementor(HEADER_ID),
        "footer": elementor(FOOTER_ID),
        "pages": [],
        "posts": [],
        "menu": [],
    }

    for pid, p in posts.items():
        if p[7] != "publish" or p[20] not in ("page", "post"):
            continue
        m = meta.get(pid, {})
        item = {
            "id": int(pid),
            "slug": p[11],
            "title": p[5],
            "date": p[2],
            "modified": p[14],
            "content": p[4],
            "excerpt": p[6],
            "seo_title": m.get("_yoast_wpseo_title", ""),
            "seo_desc": m.get("_yoast_wpseo_metadesc", ""),
        }
        if p[20] == "page":
            item["elementor"] = elementor(pid) if m.get("_elementor_edit_mode") == "builder" else None
            out["pages"].append(item)
        else:
            item["image"] = attachment_url(m["_thumbnail_id"]) if m.get("_thumbnail_id") else ""
            item["categories"] = [terms[tax[t][0]] for t in rel_by_post.get(pid, []) if t in tax and tax[t][1] == "category"]
            out["posts"].append(item)

    # Menú principal (term 461, "Menú Proyecto")
    menu_tt = next(tt for tt, (tid, kind) in tax.items() if tid == "461" and kind == "nav_menu")
    items = [posts[pid] for pid, tts in rel_by_post.items() if menu_tt in tts and pid in posts]
    items.sort(key=lambda r: int(r[19]))
    for r in items:
        m = meta.get(r[0], {})
        target = posts.get(m.get("_menu_item_object_id", ""))
        out["menu"].append({
            "id": r[0],
            "parent": m.get("_menu_item_menu_item_parent", "0"),
            "title": r[5] or (target[5] if target else ""),
            "url": m.get("_menu_item_url") or ("/" + target[11] + "/" if target else "/"),
            "type": m.get("_menu_item_type"),
        })

    out["pages"].sort(key=lambda x: x["id"])
    out["posts"].sort(key=lambda x: x["date"], reverse=True)
    with open(os.path.join(CONTENT, "site.json"), "w", encoding="utf8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)

    # Copia completa de uploads a una caché local; build.py copia solo lo que se usa.
    n = 0
    for rel, size, f in iter_wpress(wpress):
        if not rel.startswith("uploads/"):
            continue
        dst = os.path.join(UPLOADS_CACHE, rel[len("uploads/"):])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as o:
            o.write(f.read(size))
        n += 1
    print(f"{len(out['pages'])} páginas, {len(out['posts'])} artículos, {n} archivos en uploads")


if __name__ == "__main__":
    main(sys.argv[1])
