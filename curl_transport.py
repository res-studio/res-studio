"""Optional experimental HTTP client for RES Studio."""

def available():
    try:
        import curl_cffi
        return True
    except ImportError:
        return False
