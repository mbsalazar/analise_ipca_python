"""EUA: R-COICOP do BLS (CPI reagrupado em COICOP, dez/2013=100). Já publicado em COICOP; o BLS exige User-Agent identificado."""
import io, pandas as pd
from ..http import get
from .base import Conector, Resultado
URL = "https://www.bls.gov/cpi/research-series/r-coicop-data.xlsx"
def _pontuar(s: str):
    if any(ch in s for ch in "+ABCDEFGHIJKLMNOPQRSTUVWXYZ"): return None      # agrupamentos e agregados
    a, _, b = s.partition("."); return ".".join([a.zfill(2)] + list(b))
class Bls(Conector):
    pais = "USA"; nativo_coicop = True
    def coletar(self, desde=None) -> Resultado:
        rows = pd.read_excel(io.BytesIO(get(URL).content), sheet_name="Indexes", header=None)
        datas = pd.to_datetime(rows.iloc[2, 2:].astype(str).str[1:], format="%Y%m")
        corpo = rows.iloc[3:].dropna(subset=[0]); corpo = corpo[corpo[1].notna()]
        long = corpo.set_index(0).drop(columns=1); long.columns = datas
        long = long.stack().rename("indice").reset_index(); long.columns = ["cod", "data", "indice"]
        long["cod_local"] = long.cod.astype(str).map(_pontuar); long = long[long.cod_local.notna()]
        long["indice"] = pd.to_numeric(long.indice, errors="coerce"); long = long.dropna(subset=["indice"])
        if desde: long = long[long.data >= pd.Period(desde, "M").to_timestamp()]
        return Resultado(series=long.assign(pais="USA", sistema_local="COICOP1999", var_mensal=float("nan"), base="2013-12=100", fonte="BLS")
                         [["pais", "sistema_local", "cod_local", "data", "indice", "var_mensal", "base", "fonte"]])
