import re, requests, pandas as pd
UA = {"User-Agent": "Mozilla/5.0 (research; marlonbrunosalazar@yahoo.com.br)"}
def get(url, **kw):
    r = requests.get(url, headers={**UA, **kw.pop("headers", {})}, timeout=300, **kw); r.raise_for_status(); return r
def coicop_pontuado(cp):
    """'CP0111' -> '01.1.1'; 'CP01' -> '01'; 'CP01111' -> '01.1.1.1'. None se não for código puro."""
    m = re.fullmatch(r"(?:CP|)(\d{2})(\d*)", cp)
    return None if not m else ".".join([m.group(1)] + list(m.group(2)))
COLS = ["fonte", "pais", "sistema", "coicop", "data", "indice"]
