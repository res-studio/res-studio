"""Advanced, bounded breadth-first discovery of public web assets.

Operates through server.get(), so every request retains URL validation,
redirect checks and response-size limits. No login or private API access.
"""
from collections import deque
from html.parser import HTMLParser
from urllib.parse import urljoin, urldefrag, urlparse
import re

ASSET_PATTERN = re.compile(r"""(?:import\s*(?:[^'"]*?from\s*)?|import\s*\(|require\s*\()\s*['"]([^'"]+)['"]|sourceMappingURL\s*=\s*([^\s*]+)""")
CSS_PATTERN = re.compile(r"""@import\s+(?:url\()?\s*['"]?([^'"\s)]+)""")

class PageLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = []
        self.pages = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'script' and a.get('src'):
            self.assets.append(('js', a['src']))
        if tag == 'link' and a.get('href'):
            rel = a.get('rel', '').lower().split()
            if 'stylesheet' in rel: self.assets.append(('css', a['href']))
            elif 'modulepreload' in rel or 'preload' in rel and a.get('as') == 'script':
                self.assets.append(('js', a['href']))
        if tag == 'a' and a.get('href'): self.pages.append(a['href'])

def discover(start, fetch, *, max_assets=500, max_pages=10,
             max_total_bytes=100_000_000, same_origin=True, max_depth=3):
    """Return collected files and discovery diagnostics, with hard work limits."""
    if not 1 <= max_assets <= 5000 or not 1 <= max_pages <= 100:
        raise ValueError('Limites fora do intervalo permitido')
    if not 1 <= max_total_bytes <= 1_000_000_000 or not 0 <= max_depth <= 10:
        raise ValueError('Limites fora do intervalo permitido')
    origin = urlparse(start).netloc.lower()
    queue = deque([('html', start, 0)])
    queued = {start}
    seen = set()
    files, errors, requests = [], [], []
    pages = 0
    total = 0
    truncated = False
    while queue:
        kind, url, depth = queue.popleft()
        if url in seen: continue
        if len(files) >= max_assets or (kind == 'html' and pages >= max_pages):
            truncated = True
            continue
        seen.add(url)
        try:
            data, mime, final = fetch(url)
            if same_origin and urlparse(final).netloc.lower() != origin:
                errors.append(url + ': redirect fora da origem')
                continue
            if total + len(data) > max_total_bytes:
                errors.append('Limite total de bytes atingido')
                truncated = True
                break
            text = data.decode('utf-8', 'replace')
            if kind == 'html':
                if 'html' not in mime and not text.lstrip().lower().startswith(('<!doctype html', '<html')):
                    continue
                pages += 1
            total += len(data)
            files.append({'id':len(files), 'type':kind, 'url':final,
                          'size':len(data), 'content':text})
            requests.append({'url':url,'final_url':final,'size':len(data),'type':kind})
            if depth >= max_depth: continue
            candidates = []
            if kind == 'html':
                parser = PageLinks()
                parser.feed(text)
                candidates.extend(parser.assets)
                if pages < max_pages:
                    candidates.extend(('html', link) for link in parser.pages)
            elif kind == 'js':
                for match in ASSET_PATTERN.finditer(text):
                    link = match.group(1) or match.group(2)
                    if link and (link.startswith(('/', './', '../', 'http://', 'https://'))):
                        candidates.append(('js' if not link.endswith('.map') else 'map', link))
            elif kind == 'css':
                candidates.extend(('css', m.group(1)) for m in CSS_PATTERN.finditer(text))
            for target_kind, link in candidates:
                candidate, _ = urldefrag(urljoin(final, link))
                parsed = urlparse(candidate)
                if parsed.scheme not in ('http', 'https'): continue
                if same_origin and parsed.netloc.lower() != origin: continue
                if candidate not in queued:
                    queued.add(candidate)
                    queue.append((target_kind, candidate, depth + 1))
        except Exception as exc:
            errors.append(url + ': ' + str(exc)[:180])
    return {'files':files,'errors':errors,'requests':requests,
            'truncated':truncated or bool(queue),'total_bytes':total,
            'pages':pages,'discovered_urls':len(queued)}
