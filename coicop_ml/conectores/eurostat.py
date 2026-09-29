"""Eurostat HICP (prc_hicp_midx, 2015=100, COICOP 1999) e pesos (prc_hicp_inw, ‰). Consulta por país (o pedido total vira fila assíncrona)."""
import io, pandas as pd
from comum import get, coicop_pontuado, COLS
API = "https://ec.europa.eu/eurostat/api/dissemination"
def paises():
    j = get(f"{API}/statistics/1.0/data/prc_hicp_midx?format=JSON&lang=EN&freq=M&unit=I15&coicop=CP00&sinceTimePeriod=2025-01").json()
    return list(j["dimension"]["geo"]["category"]["label"].items())   # [(cod, nome)]
def _csv(ds, chave, inicio):
    df = pd.read_csv(io.StringIO(get(f"{API}/sdmx/2.1/data/{ds}/{chave}?format=SDMX-CSV&startPeriod={inicio}").text))
    df["coicop_pt"] = df.coicop.map(coicop_pontuado); return df[df.coicop_pt.notna()]
def indices(inicio="2015-01", geos=None):
    out = []
    for g, _ in (paises() if geos is None else [(x, x) for x in geos]):
        if g.startswith(("EA", "EU", "EEA")) or len(g) != 2: continue        # só países
        try: d = _csv("prc_hicp_midx", f"M.I15..{g}", inicio)
        except Exception as e: print("falhou", g, e); continue
        out.append(pd.DataFrame({"fonte": "Eurostat", "pais": g, "sistema": "COICOP1999", "coicop": d.coicop_pt,
                                 "data": pd.to_datetime(d.TIME_PERIOD), "indice": d.OBS_VALUE}))
        print(g, len(d), end=" | ", flush=True)
    return pd.concat(out, ignore_index=True)[COLS]
def pesos(inicio="2015"):
    out = []
    for g, _ in paises():
        if len(g) != 2: continue
        try: d = _csv("prc_hicp_inw", f"A..{g}", inicio)
        except Exception: continue
        out.append(pd.DataFrame({"fonte": "Eurostat", "pais": g, "coicop": d.coicop_pt, "ano": d.TIME_PERIOD.astype(int), "peso_permil": d.OBS_VALUE}))
    return pd.concat(out, ignore_index=True)
if __name__ == "__main__":
    i = indices(); i.to_csv("../dados/eurostat_indices.csv.gz", index=False); print("\n", i.pais.nunique(), "países", i.shape)
    p = pesos(); p.to_csv("../dados/eurostat_pesos.csv.gz", index=False); print(p.shape)
