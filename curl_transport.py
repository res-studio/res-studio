"""Optional curl_cffi transport; DNS-pinned, redirect-validated and size-limited."""
from io import BytesIO
from urllib.parse import urlparse, urljoin
from server import resolve_public, MAX_FILE

def available():
    try:
        import curl_cffi
        return True
    except ImportError:
        return False

def get(url):
    from curl_cffi import Curl, CurlOpt, CurlInfo
    for _ in range(5):
        host, addresses = resolve_public(url)
        parsed = urlparse(url)
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        failures = []
        next_url = None
        for address in addresses[:4]:
            curl = Curl()
            body = BytesIO()
            response_headers = {}
            exceeded = [False]
            def write(data):
                if body.tell() + len(data) > MAX_FILE:
                    exceeded[0] = True
                    return 0
                body.write(data)
                return len(data)
            def header(data):
                line = data.decode('latin1', 'replace').strip()
                if line.startswith('HTTP/'):
                    response_headers.clear()
                elif ':' in line:
                    name, value = line.split(':', 1)
                    response_headers[name.lower()] = value.strip()
                return len(data)
            try:
                curl.setopt(CurlOpt.URL, url.encode())
                curl.setopt(CurlOpt.RESOLVE, [f'{host}:{port}:{address}'.encode()])
                curl.setopt(CurlOpt.FOLLOWLOCATION, 0)
                curl.setopt(CurlOpt.CONNECTTIMEOUT, 4)
                curl.setopt(CurlOpt.TIMEOUT, 12)
                curl.setopt(CurlOpt.SSL_VERIFYPEER, 1)
                curl.setopt(CurlOpt.SSL_VERIFYHOST, 2)
                curl.setopt(CurlOpt.PROXY, b'')
                curl.setopt(CurlOpt.USERAGENT, b'RES-Studio/0.1 (read-only analysis)')
                curl.setopt(CurlOpt.WRITEFUNCTION, write)
                curl.setopt(CurlOpt.HEADERFUNCTION, header)
                curl.perform()
                status = curl.getinfo(CurlInfo.RESPONSE_CODE)
                if status in (301, 302, 303, 307, 308):
                    location = response_headers.get('location')
                    if not location:
                        raise ValueError('Redirecionamento sem destino')
                    next_url = urljoin(url, location)
                    break
                if status >= 400:
                    raise ValueError(f'HTTP {status}: resposta do servidor. URL: {url[:200]}')
                return body.getvalue(), response_headers.get('content-type', ''), url
            except ValueError:
                raise
            except Exception as exc:
                if exceeded[0]:
                    raise ValueError('Arquivo excede 2 MB') from exc
                failures.append(f'{address}: {type(exc).__name__}')
            finally:
                curl.close()
        if next_url is not None:
            url = next_url
            continue
        raise ValueError('curl_cffi: falha nos IPs validados: ' + '; '.join(failures))
    raise ValueError('Redirecionamentos excessivos')
