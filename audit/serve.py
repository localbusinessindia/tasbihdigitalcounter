#!/usr/bin/env python3
"""Local static server that EMULATES (does not replicate) Netlify behaviour:
pretty URLs, _redirects (301/301!), _headers, and 404.html with a 404 status.
Usage: python3 serve.py <site_dir> [port]
"""
import http.server, mimetypes, os, re, sys, urllib.parse, fnmatch

SITE = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
mimetypes.add_type('application/manifest+json', '.webmanifest')

def load_redirects():
    rules = []
    p = os.path.join(SITE, '_redirects')
    if os.path.exists(p):
        for line in open(p, encoding='utf8'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) >= 3:
                code = parts[2].rstrip('!')
                rules.append((parts[0], parts[1], int(code) if code.isdigit() else 301))
    return rules

def load_headers():
    out, cur = [], None
    p = os.path.join(SITE, '_headers')
    if os.path.exists(p):
        for raw in open(p, encoding='utf8'):
            if not raw.strip() or raw.lstrip().startswith('#'):
                continue
            if not raw[0].isspace():
                cur = (raw.strip(), []); out.append(cur)
            elif cur and ':' in raw:
                k, v = raw.strip().split(':', 1); cur[1].append((k.strip(), v.strip()))
    return out

REDIRECTS, HEADERS = load_redirects(), load_headers()

class H(http.server.BaseHTTPRequestHandler):
    server_version = 'NetlifyEmu'
    def log_message(self, *a): pass
    def _headers_for(self, path):
        res = {}
        for pat, items in HEADERS:
            if fnmatch.fnmatch(path, pat.replace('/*', '/*')) or pat == path:
                for k, v in items: res[k] = v
        return res
    def _resolve(self, path):
        p = urllib.parse.unquote(path)
        cand = [p.lstrip('/')]
        if p.endswith('/'): cand = [p.lstrip('/') + 'index.html']
        else: cand += [p.lstrip('/') + '.html', p.lstrip('/') + '/index.html']
        for c in cand:
            f = os.path.normpath(os.path.join(SITE, c))
            if f.startswith(SITE) and os.path.isfile(f):
                return f
        return None
    def _send(self, code, body=b'', ctype='text/html; charset=utf-8', extra=None, head=False):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        for k, v in (extra or {}).items(): self.send_header(k, v)
        self.end_headers()
        if not head: self.wfile.write(body)
    def do_HEAD(self): self.do_GET(head=True)
    def do_GET(self, head=False):
        u = urllib.parse.urlsplit(self.path)
        path = u.path
        for src, dst, code in REDIRECTS:
            hit = src == path or (src.endswith('/*') and path.startswith(src[:-1]))
            if not hit: continue
            if code in (200, 404):  # rewrite: serve dst with the given status
                f = os.path.join(SITE, dst.lstrip('/'))
                return self._send(code, open(f, 'rb').read() if os.path.isfile(f) else b'', extra=self._headers_for(path), head=head)
            loc = dst + (('?' + u.query) if u.query else '')
            return self._send(code, b'', extra={'Location': loc}, head=head)
        f = self._resolve(path)
        extra = self._headers_for(path)
        if f:
            ctype = mimetypes.guess_type(f)[0] or 'application/octet-stream'
            if ctype.startswith('text/') or ctype in ('application/javascript', 'application/json'):
                ctype += '; charset=utf-8'
            return self._send(200, open(f, 'rb').read(), ctype, extra, head)
        nf = os.path.join(SITE, '404.html')
        body = open(nf, 'rb').read() if os.path.exists(nf) else b'Not found'
        return self._send(404, body, extra=extra, head=head)

if __name__ == '__main__':
    http.server.ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()
