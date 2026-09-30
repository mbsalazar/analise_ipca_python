"""Eurostat HICP: índice (prc_hicp_midx, 2015=100, COICOP 1999) e pesos (prc_hicp_inw, ‰). Consulta por país."""
import io, pandas as pd
from ..coicop import pontuar
from ..http import get
from ..paises import iso3
from .base import Conector, Resultado
API = "https://ec.europa.eu/eurostat/api/dissemination"
def geos():
    j = get(f"{API}/statistics/1.0/data/prc_hicp_midx?format=JSON&lang=EN&freq=M&unit=I15&coicop=CP00&sinceTimePeriod=2025-01").json()
    return [g for g in j["dimension"]["geo"]["category"]["label"] if len(g) == 2]
def _csv(ds, chave, inicio):
    df = pd.read_csv(io.StringIO(get(f"{API}/sdmx/2.1/data/{ds}/{chave}?format=SDMX-CSV&startPeriod={inicio}").text))
    df["cod"] = df.coicop.map(pontuar); return df[df.cod.notna()]
class Eurostat(Conector):
    nativo_coicop = True
    def __init__(self, paises=None): self.paises = paises      # lista ISO-3 opcional
    def coletar(self, desde=None) -> Resultado:
        ini = desde or "2015-01"; series, pesos = [], []
        for g in geos():
            p = iso3(g)
            if p is None or p == "USA" or (self.paises and p not in self.paises): continue
            try:
                d = _csv("prc_hicp_midx", f"M.I15..{g}", ini)
                w = _csv("prc_hicp_inw", f"A..{g}", ini[:4])
            except Exception as e:
                print("Eurostat: falhou", g, e); continue
            series.append(pd.DataFrame({"pais": p, "sistema_local": "COICOP1999", "cod_local": d.cod, "data": pd.to_datetime(d.TIME_PERIOD),
                                        "indice": d.OBS_VALUE, "var_mensal": float("nan"), "base": "2015=100", "fonte": "Eurostat"}))
            pesos.append(pd.DataFrame({"pais": p, "sistema_local": "COICOP1999", "cod_local": w.cod, "data": pd.to_datetime(w.TIME_PERIOD.astype(str) + "-01"),
                                       "peso": w.OBS_VALUE, "escala": "permil", "fonte": "Eurostat"}))
        return Resultado(series=pd.concat(series, ignore_index=True), pesos=pd.concat(pesos, ignore_index=True))

class Eurostat2018(Conector):
    """HICP nativo em COICOP 2018 (ECOICOP ver. 2): prc_hicp_minr, 2025=100, desde jan/2025."""
    nativo_coicop = True
    def __init__(self, paises=None): self.paises = paises
    def coletar(self, desde=None) -> Resultado:
        ini = desde or "2025-01"; series = []
        for g in geos():
            p = iso3(g)
            if p is None or p == "USA" or (self.paises and p not in self.paises): continue
            try:
                d = pd.read_csv(io.StringIO(get(f"{API}/sdmx/2.1/data/prc_hicp_minr/M.I25..{g}?format=SDMX-CSV&startPeriod={ini}").text))
            except Exception as e:
                print("Eurostat2018: falhou", g, e); continue
            d["cod"] = d.coicop18.map(pontuar); d = d[d.cod.notna()]
            series.append(pd.DataFrame({"pais": p, "sistema_local": "COICOP2018", "cod_local": d.cod, "data": pd.to_datetime(d.TIME_PERIOD),
                                        "indice": d.OBS_VALUE, "var_mensal": float("nan"), "base": "2025=100", "fonte": "Eurostat"}))
        return Resultado(series=pd.concat(series, ignore_index=True))
