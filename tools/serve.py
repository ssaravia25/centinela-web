#!/usr/bin/env python3
"""
Servidor local que imita cleanUrls de Vercel, para probar las URLs reales:
  /estrategia    -> estrategia.html
  /en            -> en/index.html
  /en/strategy   -> en/strategy.html

  python3 tools/serve.py          # http://localhost:4242
  python3 tools/serve.py 5000     # otro puerto

`python3 -m http.server` no sirve: /en/strategy le da 404.
"""

import http.server
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def translate_path(self, path):
        p = super().translate_path(path)
        indice = os.path.join(p, "index.html")
        if os.path.isdir(p) and os.path.isfile(indice):
            return indice  # sin redireccion a /en/, igual que Vercel
        if not os.path.exists(p) and os.path.isfile(p + ".html"):
            return p + ".html"
        return p

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 4242
    print("Centinela en http://localhost:%d" % port)
    http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
