#!/usr/bin/env python3
"""
sync.py — mantenimiento del sitio Centinela (es · en · it · de).

NO es un build step: el repo siempre contiene HTML completo y desplegable.
Vercel no ejecuta nada y el servidor local sirve el archivo real. Esto se
corre A MANO cuando tocas partials/, site.config.json o los metadatos.

  python3 tools/sync.py           reescribe regiones, sitemap, robots y config de main.js
  python3 tools/sync.py --check   no escribe; sale != 0 si algo esta desincronizado o el lint falla
  python3 tools/sync.py --urls    lista las URLs de las paginas que existen (para QA)

Que hace:
  1. Reescribe las regiones <!-- #include X --> ... <!-- #endinclude X -->
     de cada pagina desde partials/X.<lang>.html (o partials/X.html)
  2. Expande los tokens {{...}} de esos partials: metadatos, hreflang y
     selector de idioma salen de PAGES, el resto de site.config.json
  3. Refresca en TODO el HTML el href de los CTA a la newsletter (data-cta="substack")
  4. Genera sitemap.xml (con alternates por idioma) y robots.txt
  5. Inyecta la config del formulario en el bloque /* #config */ de assets/js/main.js
  6. Lint: idioma de cada pagina, enlaces internos, anclas, copy vetado, formulario
"""

import html
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "tools" / "site.config.json").read_text(encoding="utf-8"))

BASE = CFG["site"]["base_url"].rstrip("/")

# ---------------------------------------------------------------- idiomas ---
# El orden de este diccionario es el orden del selector.
LANGS = {
    "es": {"html_lang": "es", "og_locale": "es_ES", "dir": "",   "nombre": "Español",  "rotulo": "Idioma"},
    "en": {"html_lang": "en", "og_locale": "en_GB", "dir": "en", "nombre": "English",  "rotulo": "Language"},
    "it": {"html_lang": "it", "og_locale": "it_IT", "dir": "it", "nombre": "Italiano", "rotulo": "Lingua"},
    "de": {"html_lang": "de", "og_locale": "de_DE", "dir": "de", "nombre": "Deutsch",  "rotulo": "Sprache"},
}
DEFAULT_LANG = "es"

# ------------------------------------------------------------------ grupos ---
# Un grupo = la misma pagina en todos sus idiomas. Aqui va lo que no se traduce.
GROUPS = {
    "home":       {"nav": "home",       "robots": "index, follow",   "sitemap": True,  "prioridad": "1.0", "changefreq": "weekly"},
    "newsletter": {"nav": "newsletter", "robots": "index, follow",   "sitemap": True,  "prioridad": "0.8", "changefreq": "monthly"},
    "estrategia": {"nav": "estrategia", "robots": "index, follow",   "sitemap": True,  "prioridad": "0.8", "changefreq": "monthly"},
    "sobre":      {"nav": "sobre",      "robots": "index, follow",   "sitemap": True,  "prioridad": "0.6", "changefreq": "monthly"},
    # Sin enlace en el nav y fuera del sitemap: solo se llega desde el plan Access.
    "waitlist":   {"nav": None,         "robots": "noindex, follow", "sitemap": False, "prioridad": "0.1", "changefreq": "monthly"},
}

# ---------------------------------------------------------------- paginas ---
# Fuente unica de verdad de los metadatos. Anadir una pagina = anadir una fila.
PAGES = {
    # ---- Español (raíz) ---------------------------------------------------
    "index.html": {
        "group": "home", "lang": "es", "url": "/",
        "title": "Centinela · Inversión sistemática multi-activo",
        "desc": "Una forma más clara de invertir. Estrategia sistemática multi-activo, ETFs de bajo coste "
                "y una lectura estructurada del mercado para invertir con más criterio. Empieza gratis.",
        "og_desc": "Una forma más clara de invertir. Estrategia sistemática, ETFs de bajo coste y una "
                   "lectura estructurada del mercado.",
    },
    "newsletter.html": {
        "group": "newsletter", "lang": "es", "url": "/newsletter",
        "title": "Newsletter · Centinela",
        "desc": "La newsletter gratuita de Centinela. Breve, clara y útil para entender el mercado, la "
                "lógica de la estrategia y construir una cartera con más criterio.",
        "og_desc": "La puerta de entrada a Centinela. Newsletter gratuita para invertir con más criterio.",
    },
    "estrategia.html": {
        "group": "estrategia", "lang": "es", "url": "/estrategia",
        "title": "Estrategia · Centinela",
        "desc": "El método completo de Centinela: diversificación por ciclos, momentum relativo, filtro de "
                "tendencia y rebalanceo mensual. Cinco bloques y el rendimiento del backtest 2020–2026 con "
                "activos reales, frente al 60/40 y al SPY.",
        "og_desc": "Diversificación por ciclos, momentum, filtro de tendencia y rebalanceo mensual. Un "
                   "método completo, con reglas claras.",
    },
    "sobre-centinela.html": {
        "group": "sobre", "lang": "es", "url": "/sobre-centinela",
        "title": "Sobre Centinela · Filosofía y valores",
        "desc": "Momentum, disciplina, independencia e integridad. Centinela nace con la idea de entender "
                "mejor el mercado para tomar decisiones de inversión con más criterio.",
        "og_desc": "Momentum, disciplina, independencia e integridad. La filosofía detrás de Centinela.",
    },
    "waitlist.html": {
        "group": "waitlist", "lang": "es", "url": "/waitlist",
        "title": "Súmate a la waitlist · Centinela Access",
        "desc": "Centinela Access aún no está abierto al público. Súmate a la waitlist y sé de los primeros "
                "en acceder a la estrategia, las carteras y su seguimiento.",
    },

    # ---- English (/en) ----------------------------------------------------
    "en/index.html": {
        "group": "home", "lang": "en", "url": "/en/",
        "title": "Centinela · Systematic multi-asset investing",
        "desc": "A clearer way to invest. A systematic multi-asset strategy, low-cost ETFs and a structured "
                "reading of the market to invest with sounder judgement. Start for free.",
        "og_desc": "A clearer way to invest. A systematic strategy, low-cost ETFs and a structured reading "
                   "of the market.",
    },
    "en/newsletter.html": {
        "group": "newsletter", "lang": "en", "url": "/en/newsletter",
        "title": "Newsletter · Centinela",
        "desc": "Centinela's free newsletter. Short, clear and useful for understanding the market and the "
                "logic of the strategy, and for building a portfolio with sounder judgement.",
        "og_desc": "The gateway to Centinela. A free newsletter to invest with sounder judgement.",
    },
    "en/strategy.html": {
        "group": "estrategia", "lang": "en", "url": "/en/strategy",
        "title": "Strategy · Centinela",
        "desc": "Centinela's full method: diversification across cycles, relative momentum, trend filter "
                "and monthly rebalancing. Five blocks and the 2020–2026 backtest performance with real "
                "assets, against a 60/40 portfolio and SPY.",
        "og_desc": "Diversification across cycles, momentum, trend filter and monthly rebalancing. A "
                   "complete method with clear rules.",
    },
    "en/about.html": {
        "group": "sobre", "lang": "en", "url": "/en/about",
        "title": "About Centinela · Philosophy and values",
        "desc": "Momentum, discipline, independence and integrity. Centinela was born from the idea of "
                "understanding the market better in order to make investment decisions with sounder judgement.",
        "og_desc": "Momentum, discipline, independence and integrity. The philosophy behind Centinela.",
    },
    "en/waitlist.html": {
        "group": "waitlist", "lang": "en", "url": "/en/waitlist",
        "title": "Join the waitlist · Centinela Access",
        "desc": "Centinela Access is not open to the public yet. Join the waitlist and be among the first "
                "to access the strategy, the portfolios and their tracking.",
    },

    # ---- Italiano (/it) ---------------------------------------------------
    "it/index.html": {
        "group": "home", "lang": "it", "url": "/it/",
        "title": "Centinela · Investimento sistematico multi-asset",
        "desc": "Un modo più chiaro di investire. Strategia sistematica multi-asset, ETF a basso costo e "
                "una lettura strutturata del mercato per investire con più criterio. Inizia gratis.",
        "og_desc": "Un modo più chiaro di investire. Strategia sistematica, ETF a basso costo e una "
                   "lettura strutturata del mercato.",
    },
    "it/newsletter.html": {
        "group": "newsletter", "lang": "it", "url": "/it/newsletter",
        "title": "Newsletter · Centinela",
        "desc": "La newsletter gratuita di Centinela. Breve, chiara e utile per capire il mercato, la "
                "logica della strategia e costruire un portafoglio con più criterio.",
        "og_desc": "La porta d'ingresso a Centinela. Newsletter gratuita per investire con più criterio.",
    },
    "it/strategia.html": {
        "group": "estrategia", "lang": "it", "url": "/it/strategia",
        "title": "Strategia · Centinela",
        "desc": "Il metodo completo di Centinela: diversificazione per cicli, momentum relativo, filtro di "
                "tendenza e ribilanciamento mensile. Cinque blocchi e il rendimento del backtest 2020–2026 "
                "con asset reali, a confronto con il 60/40 e lo SPY.",
        "og_desc": "Diversificazione per cicli, momentum, filtro di tendenza e ribilanciamento mensile. "
                   "Un metodo completo, con regole chiare.",
    },
    "it/chi-siamo.html": {
        "group": "sobre", "lang": "it", "url": "/it/chi-siamo",
        "title": "Chi siamo · Filosofia e valori di Centinela",
        "desc": "Momentum, disciplina, indipendenza e integrità. Centinela nasce dall'idea di capire meglio "
                "il mercato per prendere decisioni di investimento con più criterio.",
        "og_desc": "Momentum, disciplina, indipendenza e integrità. La filosofia dietro Centinela.",
    },
    "it/waitlist.html": {
        "group": "waitlist", "lang": "it", "url": "/it/waitlist",
        "title": "Entra nella waitlist · Centinela Access",
        "desc": "Centinela Access non è ancora aperto al pubblico. Entra nella waitlist e sii tra i "
                "primi ad accedere alla strategia, ai portafogli e al loro monitoraggio.",
    },

    # ---- Deutsch (/de) ----------------------------------------------------
    "de/index.html": {
        "group": "home", "lang": "de", "url": "/de/",
        "title": "Centinela · Systematisches Multi-Asset-Investieren",
        "desc": "Eine klarere Art zu investieren. Eine systematische Multi-Asset-Strategie, kostengünstige "
                "ETFs und eine strukturierte Marktanalyse, um mit mehr Urteilsvermögen zu investieren. "
                "Kostenlos starten.",
        "og_desc": "Eine klarere Art zu investieren. Systematische Strategie, kostengünstige ETFs und eine "
                   "strukturierte Marktanalyse.",
    },
    "de/newsletter.html": {
        "group": "newsletter", "lang": "de", "url": "/de/newsletter",
        "title": "Newsletter · Centinela",
        "desc": "Der kostenlose Newsletter von Centinela. Kurz, klar und nützlich, um den Markt und die "
                "Logik der Strategie zu verstehen und ein Portfolio mit mehr Urteilsvermögen aufzubauen.",
        "og_desc": "Der Einstieg in Centinela. Kostenloser Newsletter, um mit mehr Urteilsvermögen zu "
                   "investieren.",
    },
    "de/strategie.html": {
        "group": "estrategia", "lang": "de", "url": "/de/strategie",
        "title": "Strategie · Centinela",
        "desc": "Die vollständige Methode von Centinela: Diversifikation über Zyklen, relatives Momentum, "
                "Trendfilter und monatliches Rebalancing. Fünf Bausteine und die Backtest-Performance "
                "2020–2026 mit realen Anlagen im Vergleich zu 60/40 und SPY.",
        "og_desc": "Diversifikation über Zyklen, Momentum, Trendfilter und monatliches Rebalancing. Eine "
                   "vollständige Methode mit klaren Regeln.",
    },
    "de/ueber-centinela.html": {
        "group": "sobre", "lang": "de", "url": "/de/ueber-centinela",
        "title": "Über Centinela · Philosophie und Werte",
        "desc": "Momentum, Disziplin, Unabhängigkeit und Integrität. Centinela entstand aus der Idee, den "
                "Markt besser zu verstehen, um Anlageentscheidungen mit mehr Urteilsvermögen zu treffen.",
        "og_desc": "Momentum, Disziplin, Unabhängigkeit und Integrität. Die Philosophie hinter Centinela.",
    },
    "de/waitlist.html": {
        "group": "waitlist", "lang": "de", "url": "/de/waitlist",
        "title": "Warteliste · Centinela Access",
        "desc": "Centinela Access ist noch nicht öffentlich zugänglich. Trag dich in die Warteliste ein und "
                "gehöre zu den Ersten mit Zugang zur Strategie, zu den Portfolios und ihrer Verfolgung.",
    },
}

REGIONES_OBLIGATORIAS = ("head", "nav", "footer")
REGIONES_OPCIONALES = ("aviso",)

# Copy vetado (feedback de Toni, Centinela-Web-Proceso.md §8). Se busca sobre el
# texto visible, sin etiquetas, en todos los idiomas.
VETADO = {
    "*":  [r"100\s?%", r"copy[\s-]?trading", r"discord"],
    "es": [r"discrecionalidad"],
    "en": [r"\bdiscretion"],
    "it": [r"discrezional"],
    "de": [r"ermessen", r"diskretion"],
}


# ------------------------------------------------------- mapa de paginas ---
def validar_pages():
    vistos, urls = set(), set()
    for f, m in PAGES.items():
        clave = (m["group"], m["lang"])
        assert clave not in vistos, "grupo+idioma repetido: %s" % (clave,)
        assert m["url"] not in urls, "url repetida: %s" % m["url"]
        assert m["group"] in GROUPS, "grupo desconocido en %s" % f
        d = LANGS[m["lang"]]["dir"]
        if d:
            assert f.startswith(d + "/") and (m["url"] == "/" + d or m["url"].startswith("/" + d + "/")), \
                "%s no vive bajo /%s" % (f, d)
        else:
            assert "/" not in f, "%s deberia estar en la raiz" % f
        vistos.add(clave)
        urls.add(m["url"])


def existentes():
    return {f: m for f, m in PAGES.items() if (ROOT / f).exists()}


def por_grupo(pags):
    g = {}
    for f, m in pags.items():
        g.setdefault(m["group"], {})[m["lang"]] = m
    return g


# ----------------------------------------------------------------- tokens ---
def hreflang_block(grupo):
    filas = []
    for code in LANGS:
        t = grupo.get(code)
        if t:
            filas.append('<link rel="alternate" hreflang="%s" href="%s" />' % (code, BASE + t["url"]))
    if grupo.get(DEFAULT_LANG):
        filas.append('<link rel="alternate" hreflang="x-default" href="%s" />' % (BASE + grupo[DEFAULT_LANG]["url"]))
    return "\n".join(filas)


def selector(grupo, home, lang):
    """Selector de idioma. El activo es un <span>, no un enlace a si mismo.
    Rutas relativas: funciona igual en local, en preview y en produccion."""
    items = []
    for code, info in LANGS.items():
        if code == lang:
            items.append('<span class="lang__item" aria-current="true" lang="%s" title="%s">%s</span>'
                         % (code, info["nombre"], code.upper()))
            continue
        destino = grupo.get(code) or home.get(code)
        if not destino:
            continue  # idioma sin paginas todavia
        items.append('<a class="lang__item" href="%s" hreflang="%s" lang="%s" title="%s" aria-label="%s">%s</a>'
                     % (destino["url"], code, code, info["nombre"], info["nombre"], code.upper()))
    return ('<nav class="lang" aria-label="%s">\n  %s\n</nav>'
            % (LANGS[lang]["rotulo"], "\n  ".join(items)))


def tokens_for(meta, grupos):
    esc = lambda s: html.escape(s, quote=True)
    lang = meta["lang"]
    grupo = grupos[meta["group"]]
    return {
        "titulo": esc(meta["title"]),
        "descripcion": esc(meta["desc"]),
        "og_descripcion": esc(meta.get("og_desc", meta["desc"])),
        "canonical": BASE + meta["url"],
        "robots": GROUPS[meta["group"]]["robots"],
        "og_locale": LANGS[lang]["og_locale"],
        "og_alt_block": "\n".join(
            '<meta property="og:locale:alternate" content="%s" />' % LANGS[c]["og_locale"]
            for c in LANGS if c != lang and c in grupo
        ),
        "hreflang_block": hreflang_block(grupo),
        "lang_switcher": selector(grupo, grupos.get("home", {}), lang),
        "responsable": esc(CFG["legal"]["responsable"]),
        "email_legal": esc(CFG["contacto"]["email"]),
        "anio": str(date.today().year),
    }


TOKEN_RE = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")
# Token solo en su linea: su valor puede ser multilinea y hereda la sangria.
TOKEN_LINEA_RE = re.compile(r"^([ \t]*)\{\{\s*([a-z_]+)\s*\}\}[ \t]*$", re.M)
BORRAR = "\x00borrar\x00"


def sangrar(texto, sangria):
    return "\n".join((sangria + l) if l.strip() else "" for l in texto.split("\n"))


def expand(texto, tok):
    faltan = set()

    def linea(m):
        k = m.group(2)
        if k not in tok:
            faltan.add(k)
            return m.group(0)
        return sangrar(tok[k], m.group(1)) if tok[k] else BORRAR

    def suelto(m):
        k = m.group(1)
        if k not in tok:
            faltan.add(k)
            return m.group(0)
        return tok[k]

    texto = TOKEN_LINEA_RE.sub(linea, texto)
    texto = "\n".join(l for l in texto.split("\n") if l != BORRAR)
    texto = TOKEN_RE.sub(suelto, texto)
    if faltan:
        raise SystemExit("  ERROR: tokens desconocidos: %s" % sorted(faltan))
    return texto


# --------------------------------------------------------------- regiones ---
def region_re(nombre):
    return re.compile(
        r"^([ \t]*)<!--\s*#include\s+%s\s*-->.*?<!--\s*#endinclude\s+%s\s*-->" % (nombre, nombre),
        re.S | re.M,
    )


def sin_regiones(texto):
    for n in REGIONES_OBLIGATORIAS + REGIONES_OPCIONALES:
        texto = region_re(n).sub("", texto)
    return texto


def marcar_actual(nav, nav_id):
    """aria-current en TODAS las copias del enlace: el nav va dos veces (barra y menu movil)."""
    if not nav_id:
        return nav
    return nav.replace('data-nav="%s"' % nav_id, 'data-nav="%s" aria-current="page"' % nav_id)


def cargar_partials():
    partials = {}
    for nombre in REGIONES_OBLIGATORIAS + REGIONES_OPCIONALES:
        for lang in LANGS:
            p = ROOT / "partials" / ("%s.%s.html" % (nombre, lang))
            if not p.exists():
                p = ROOT / "partials" / ("%s.html" % nombre)
            if p.exists():
                partials[(nombre, lang)] = p.read_text(encoding="utf-8").strip("\n")
    return partials


# Los CTA a la newsletter tambien viven en el cuerpo de las paginas, fuera de las
# regiones. En vez de un token (que se congelaria) va la URL real y se refresca
# en cada pasada, asi que cambiar site.newsletter_url la actualiza en todo el sitio.
CTA_RE = re.compile(r'href="[^"]*"(\s+data-cta="substack")')


def render(meta, pagina, partials, grupos, errores, f):
    tok = tokens_for(meta, grupos)
    aviso_pendiente = not CFG["contacto"]["email"]
    for nombre in REGIONES_OBLIGATORIAS + REGIONES_OPCIONALES:
        rx = region_re(nombre)
        if not rx.search(pagina):
            if nombre in REGIONES_OBLIGATORIAS:
                errores.append("%s: falta la region #include %s" % (f, nombre))
            continue
        cuerpo = partials.get((nombre, meta["lang"]))
        if cuerpo is None:
            errores.append("%s: no existe partials/%s.%s.html" % (f, nombre, meta["lang"]))
            continue
        if nombre == "nav":
            cuerpo = marcar_actual(cuerpo, GROUPS[meta["group"]]["nav"])
        if nombre == "aviso" and aviso_pendiente:
            # Sin email de contacto el aviso no es valido: no se publica nada.
            cuerpo = "<!-- Aviso de privacidad pendiente: falta contacto.email en tools/site.config.json -->"
        cuerpo = expand(cuerpo, tok)
        pagina = rx.sub(
            lambda m: "%s<!-- #include %s -->\n%s\n%s<!-- #endinclude %s -->"
            % (m.group(1), nombre, sangrar(cuerpo, m.group(1)), m.group(1), nombre),
            pagina,
        )
    return CTA_RE.sub(lambda m: 'href="%s"%s' % (CFG["site"]["newsletter_url"], m.group(1)), pagina)


# ------------------------------------------------------------------- lint ---
HTML_LANG_RE = re.compile(r'<html\s+lang="([^"]*)"')
A_RE = re.compile(r"<a\b[^>]*>", re.I)
HREF_RE = re.compile(r'\bhref="([^"]*)"')
ID_RE = re.compile(r'\bid="([^"]+)"')


def texto_visible(pagina):
    t = re.sub(r"<(script|style)\b.*?</\1>", " ", pagina, flags=re.S | re.I)
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return html.unescape(t)


def lint_previo(f, meta, original, errores):
    m = HTML_LANG_RE.search(original)
    esperado = LANGS[meta["lang"]]["html_lang"]
    if not m or m.group(1) != esperado:
        errores.append('%s: <html lang> deberia ser "%s"' % (f, esperado))
    if "{{" in sin_regiones(original):
        errores.append("%s: hay {{tokens}} fuera de una region #include (se congelarian)" % f)


def lint_final(renderizadas, errores):
    por_url = {m["url"]: (f, m) for f, (m, _) in renderizadas.items()}
    ids = {f: set(ID_RE.findall(h)) for f, (_, h) in renderizadas.items()}

    for f, (meta, pagina) in renderizadas.items():
        lang = meta["lang"]

        if re.search(r'(href|src)="assets/', pagina):
            errores.append("%s: ruta relativa a assets/ (se rompe bajo /en/...)" % f)
        if pagina.count('data-cta="substack"') != len(CTA_RE.findall(pagina)):
            errores.append('%s: hay un data-cta="substack" sin href justo delante' % f)

        for tag in A_RE.findall(pagina):
            h = HREF_RE.search(tag)
            if not h:
                continue
            href = h.group(1)
            if href.startswith("#"):
                if href[1:] and href[1:] not in ids[f]:
                    errores.append("%s: ancla %s no existe en la pagina" % (f, href))
                continue
            if not href.startswith("/"):
                continue
            ruta, _, frag = href.partition("#")
            if ruta.endswith(".html"):
                errores.append("%s: enlace con .html (%s); usa la URL limpia" % (f, href))
                continue
            destino = por_url.get(ruta)
            if not destino:
                if not (ROOT / ruta.lstrip("/")).is_file():
                    errores.append("%s: enlace interno roto %s" % (f, href))
                continue
            dfile, dmeta = destino
            if dmeta["lang"] != lang and "hreflang=" not in tag:
                errores.append("%s: enlace %s lleva a otro idioma (%s)" % (f, href, dmeta["lang"]))
            if frag and frag not in ids[dfile]:
                errores.append("%s: ancla #%s no existe en %s" % (f, frag, dfile))

        es_waitlist = meta["group"] == "waitlist"
        n_web = pagina.count('name="web"')
        n_form = pagina.count('id="form-waitlist"')
        if es_waitlist and (n_web != 1 or n_form != 1):
            errores.append("%s: la waitlist necesita 1 honeypot name=\"web\" y 1 #form-waitlist (hay %d y %d)"
                           % (f, n_web, n_form))
        if not es_waitlist and n_web:
            errores.append('%s: name="web" fuera de la waitlist' % f)

        visible = texto_visible(pagina)
        for patron in VETADO["*"] + VETADO.get(lang, []):
            hit = re.search(patron, visible, re.I)
            if hit:
                errores.append('%s: copy vetado "%s"' % (f, hit.group(0)))


# ---------------------------------------------------------------- sitemap ---
def build_sitemap(pags, grupos):
    filas = []
    for f, m in pags.items():
        g = GROUPS[m["group"]]
        if not g["sitemap"]:
            continue
        alternos = [
            '    <xhtml:link rel="alternate" hreflang="%s" href="%s%s"/>' % (c, BASE, grupos[m["group"]][c]["url"])
            for c in LANGS if c in grupos[m["group"]]
        ]
        if DEFAULT_LANG in grupos[m["group"]]:
            alternos.append('    <xhtml:link rel="alternate" hreflang="x-default" href="%s%s"/>'
                            % (BASE, grupos[m["group"]][DEFAULT_LANG]["url"]))
        filas.append(
            "  <url>\n    <loc>%s%s</loc>\n%s\n    <changefreq>%s</changefreq>\n    <priority>%s</priority>\n  </url>"
            % (BASE, m["url"], "\n".join(alternos), g["changefreq"], g["prioridad"])
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(filas)
        + "\n</urlset>\n"
    )


def build_robots():
    return "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % BASE


CONFIG_BLOCK_RE = re.compile(r"(/\* #config \*/)(.*?)(/\* #endconfig \*/)", re.S)


def build_js_config():
    f = CFG["form"]
    return (
        "\nvar CONFIG = {\n"
        "  endpoint: %s,\n"
        "  token: %s,\n"
        "  avisoVersion: %s\n"
        "};\n"
        % tuple(json.dumps(f[k], ensure_ascii=False) for k in ("endpoint", "token", "aviso_version"))
    )


# ------------------------------------------------------------------- main ---
def main():
    validar_pages()
    pags = existentes()

    if "--urls" in sys.argv:
        for m in pags.values():
            print(m["url"])
        return 0

    check = "--check" in sys.argv

    if CFG["form"]["endpoint"] and not CFG["contacto"]["email"]:
        print("  ERROR: form.endpoint esta puesto pero contacto.email esta vacio.\n"
              "  El formulario no puede recoger datos sin aviso de privacidad con email de contacto.")
        return 1

    grupos = por_grupo(pags)
    partials = cargar_partials()
    cambios, errores = [], []

    def escribir(path, nuevo):
        actual = path.read_text(encoding="utf-8") if path.exists() else None
        if actual == nuevo:
            return
        cambios.append(path.relative_to(ROOT))
        if not check:
            path.write_text(nuevo, encoding="utf-8")

    renderizadas = {}
    for f, meta in pags.items():
        original = (ROOT / f).read_text(encoding="utf-8")
        lint_previo(f, meta, original, errores)
        nuevo = render(meta, original, partials, grupos, errores, f)
        renderizadas[f] = (meta, nuevo)
        escribir(ROOT / f, nuevo)

    lint_final(renderizadas, errores)

    escribir(ROOT / "sitemap.xml", build_sitemap(pags, grupos))
    escribir(ROOT / "robots.txt", build_robots())

    js = ROOT / "assets" / "js" / "main.js"
    src = js.read_text(encoding="utf-8")
    if CONFIG_BLOCK_RE.search(src):
        escribir(js, CONFIG_BLOCK_RE.sub(lambda m: m.group(1) + build_js_config() + m.group(3), src))
    else:
        errores.append("assets/js/main.js: falta el bloque /* #config */ ... /* #endconfig */")

    # Traducciones incompletas: no rompen, pero se avisan.
    for g, por_lang in grupos.items():
        faltan = [c for c in LANGS if c not in por_lang]
        if faltan:
            print("  AVISO: el grupo '%s' no tiene version en %s" % (g, ", ".join(faltan)))

    if errores:
        print("  LINT:")
        for e in errores:
            print("    ✗ %s" % e)

    if check:
        if cambios:
            print("  DESINCRONIZADO. Corre `python3 tools/sync.py`:")
            for c in cambios:
                print("    - %s" % c)
        if cambios or errores:
            return 1
        print("  OK: %d paginas sincronizadas, lint limpio." % len(pags))
        return 0

    if cambios:
        for c in cambios:
            print("  actualizado  %s" % c)
    else:
        print("  Sin cambios.")

    pend = []
    if not CFG["form"]["endpoint"]:
        pend.append("form.endpoint vacio: la waitlist muestra el enlace a la newsletter en vez del formulario")
    if not CFG["contacto"]["email"]:
        pend.append("contacto.email vacio: el aviso de privacidad no se publica")
    if pend:
        print("\n  PENDIENTE:")
        for p in pend:
            print("    ! %s" % p)
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
