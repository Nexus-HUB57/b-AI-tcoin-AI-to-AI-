#!/usr/bin/env python3
"""MyLink Routes Service — microsservico standalone (porta 18446).
Serve APENAS as rotas novas (feed write / swap / myvideo) via mylink_routes (18/18 testado).
O daemon principal (18445) NAO e tocado — GETs continuam nele. nginx faz o split."""
import json
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
import mylink_routes as M

class H(BaseHTTPRequestHandler):
    def _j(self, o, code=200):
        b = json.dumps(o, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(b)))
        self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        q = parse_qs(urlparse(self.path).query)
        if path.endswith('/health') or path.endswith('/healthz'):
            return self._j({'status': 'ok', 'service': 'mylink-routes', 'port': 18446})
        r = M.try_get(path, q)
        if r is not None: return self._j(r[0], r[1])
        self._j({'error': 'not_found', 'path': path, 'service': 'mylink-routes'}, 404)
    def do_POST(self):
        path = unquote(urlparse(self.path).path)
        try:
            ln = int(self.headers.get('Content-Length', 0) or 0)
            body = json.loads(self.rfile.read(ln).decode('utf-8', 'replace') or '{}') if 0 < ln < 16384 else {}
        except Exception: body = {}
        r = M.try_post(path, body)
        if r is not None: return self._j(r[0], r[1])
        self._j({'error': 'not_found', 'path': path, 'service': 'mylink-routes'}, 404)

if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', 18446), H).serve_forever()
