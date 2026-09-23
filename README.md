# Centinela

Web de **Centinela**, estrategia de inversión sistemática multi-activo, en cuatro idiomas
(español, inglés, italiano y alemán).

Sitio **estático, sin build**: HTML + CSS + JS vanilla, sin dependencias más allá de
Google Fonts. Se publica en GitHub Pages.

## Estructura

| | |
|---|---|
| `index.html`, `estrategia.html`, … | páginas en español (raíz) |
| `en/`, `it/`, `de/` | las mismas páginas traducidas |
| `assets/css/styles.css` | único archivo de estilos; design system en `:root` |
| `assets/js/main.js` | único script: menú móvil, reveal-on-scroll, formulario de waitlist |
| `partials/` | nav, footer, `<head>` y aviso de privacidad, por idioma |
| `tools/sync.py` | reescribe esas regiones en las 20 páginas y genera `sitemap.xml` y `robots.txt` |

## Trabajar con el sitio

```bash
python3 tools/serve.py          # http://localhost:4242, con URLs limpias
python3 tools/sync.py           # tras tocar partials/, tools/site.config.json o los metadatos
python3 tools/sync.py --check   # no escribe; falla si algo quedó desincronizado
```

`sync.py --check` también revisa el idioma de cada página, los enlaces internos y las anclas.
El workflow de GitHub Actions lo ejecuta antes de publicar: si falla, no se publica nada.

`partials/` y `tools/` viven en el repo pero **no** se publican: el workflow sube solo el HTML,
`assets/`, `robots.txt` y `sitemap.xml`.
