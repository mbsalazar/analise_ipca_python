import time, requests
UA = {"User-Agent": "Mozilla/5.0 (research; marlonbrunosalazar@yahoo.com.br)"}
def get(url, tentativas=4, **kw):
    """GET com retry exponencial (2, 4, 8 s)."""
    for i in range(tentativas):
        try:
            r = requests.get(url, headers={**UA, **kw.pop("headers", {})}, timeout=300, **kw); r.raise_for_status(); return r
        except requests.RequestException:
            if i == tentativas - 1: raise
            time.sleep(2 ** (i + 1))
