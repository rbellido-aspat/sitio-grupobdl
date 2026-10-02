# sitio-grupobdl

Sitio estático de **Grupo BDL** (www.grupobdl.cl), reconstruido a partir del respaldo WordPress
`www.grupobdl.cl-20230405-155746-djc73j.wpress` (WordPress 5.9 con Elementor, tema Sydney).

- Sitio temporal: https://black-forest-0b8f47010.5.azurestaticapps.net
- Dominio final: https://www.grupobdl.cl
- Publicación: Azure Static Web Apps, se despliega solo la carpeta `site/` al hacer push a `main`.

## Estructura

| Ruta | Contenido |
|---|---|
| `site/` | Sitio publicado (HTML, CSS, JS e imágenes). Se genera, no se edita a mano. |
| `content/site.json` | Contenido extraído del respaldo: páginas Elementor, 64 artículos, menú, cabecera y pie. |
| `tools/export_wpress.py` | Lee el `.wpress` y genera `content/site.json` y la caché local `content/_uploads/` (no se versiona). |
| `tools/build.py` | Genera `site/` desde `content/site.json`. |
| `tools/assets/` | `styles.css` y `main.js` del sitio. |
| `staticwebapp.config.json` | Redirecciones de URLs antiguas de WordPress, página 404 y cabeceras. |

## Regenerar el sitio

```bash
python tools/export_wpress.py "../www.grupobdl.cl-20230405-155746-djc73j.wpress"
python tools/build.py
```

El primer comando solo es necesario si cambia el respaldo o si falta `content/_uploads/`.
Para editar textos, cambia `content/site.json` y vuelve a ejecutar `build.py`.

## Contacto por WhatsApp

Los formularios del sitio original (pestañas Typeform de la página Empresa, comentarios y enlaces a
formularios de contacto) se reemplazaron por enlaces a WhatsApp +56 9 9243 3573. El número y el
mensaje por defecto están en `WHATSAPP_NUMBER` y `WHATSAPP_DEFAULT` dentro de `tools/build.py`.
Además, cada página tiene un botón flotante de WhatsApp y los botones "Solicitar Servicio" abren
WhatsApp con un mensaje que indica desde qué página escribe el visitante.

## URLs

Se mantienen las mismas rutas del WordPress (`/empresa-grupobdl/`, `/metodo-de-madurez/`, etc.) y las
imágenes conservan su ruta `/wp-content/uploads/...`, así los enlaces existentes y el SEO no se pierden.
