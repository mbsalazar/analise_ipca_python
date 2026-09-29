"""OCDE (SDMX): CPI por COICOP, fluxos COICOP 2018 e 1999. Índice mensal com base própria (BASE_PER)."""
import io, pandas as pd
from ..coicop import pontuar
from ..http import get
from ..paises import iso3
from .base import Conector, Resultado
FLUXOS = {"COICOP2018": "DSD_PRICES_COICOP2018@DF_PRICES_C2018_ALL", "COICOP1999": "DSD_PRICES@DF_PRICES_ALL"}
class Ocde(Conector):
    nativo_coicop = True
    def coletar(self, desde=None) -> Resultado:
        out = []
        for sistema, fluxo in FLUXOS.items():
            url = (f"https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,{fluxo},/.M.N.CPI.IX..N._Z"
                   f"?startPeriod={desde or '2015-01'}&dimensionAtObservation=AllDimensions")
            d = pd.read_csv(io.StringIO(get(url, headers={"Accept": "application/vnd.sdmx.data+csv"}).text))
            d["cod"] = d.EXPENDITURE.replace({"_T": "CP00"}).map(pontuar)   # _T = total (índice geral)
            d["p"] = d.REF_AREA.map(iso3); d = d[d.cod.notna() & d.p.notna()]
            out.append(pd.DataFrame({"pais": d.p, "sistema_local": sistema, "cod_local": d.cod, "data": pd.to_datetime(d.TIME_PERIOD),
                                     "indice": d.OBS_VALUE, "var_mensal": float("nan"), "base": d.BASE_PER.astype(str) + "=100", "fonte": "OCDE"}))
        return Resultado(series=pd.concat(out, ignore_index=True))
