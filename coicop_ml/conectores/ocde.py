"""OCDE (SDMX): CPI por COICOP. Dois fluxos: COICOP 2018 (DF_PRICES_C2018_ALL) e COICOP 1999 (DF_PRICES_ALL). Índice mensal, base própria (BASE_PER)."""
import io, pandas as pd
from comum import get, coicop_pontuado, COLS
FLUXOS = {"COICOP2018": "DSD_PRICES_COICOP2018@DF_PRICES_C2018_ALL", "COICOP1999": "DSD_PRICES@DF_PRICES_ALL"}
def baixar(sistema, inicio="2015-01", medida="CPI", unidade="IX", transf="_Z"):
    url = (f"https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,{FLUXOS[sistema]},/.M.N.{medida}.{unidade}..N.{transf}"
           f"?startPeriod={inicio}&dimensionAtObservation=AllDimensions")
    return pd.read_csv(io.StringIO(get(url, headers={"Accept": "application/vnd.sdmx.data+csv"}).text))
def indices(sistema, inicio="2015-01"):
    d = baixar(sistema, inicio); d["c"] = d.EXPENDITURE.map(coicop_pontuado); d = d[d.c.notna()]
    return pd.DataFrame({"fonte": "OCDE", "pais": d.REF_AREA, "sistema": sistema, "coicop": d.c,
                         "data": pd.to_datetime(d.TIME_PERIOD), "indice": d.OBS_VALUE, "base": d.BASE_PER})
if __name__ == "__main__":
    for s in FLUXOS:
        try:
            d = indices(s); d.to_csv(f"../dados/ocde_indices_{s}.csv.gz", index=False)
            print(s, d.shape, d.pais.nunique(), "áreas")
        except Exception as e: print(s, "falhou:", str(e)[:200])
