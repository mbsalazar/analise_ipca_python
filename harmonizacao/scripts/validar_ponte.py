"""Valida cada nó 'exato' da ponte 1999->2018 contra a série NATIVA de 2018 do Eurostat (2025-02..2025-12), em todos os países.
Saída: tabelas/ponte_validacao.csv (por nó de 2018: países comparados, erro médio mensal mediano em p.p., correlação mediana)."""
import sys, numpy as np, pandas as pd
from pathlib import Path
R = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(R / "src"))
from harmonizacao import armazem as A
from harmonizacao.agregar import publicado
from harmonizacao.ponte import Ponte, pontear
ser = A.ler("serie_nacional"); pes = A.ler("peso_nacional")
es = ser[(ser.fonte == "Eurostat") & ser.indice.notna() & (ser.pais != "USA")]
pub = publicado(es, pes)
p = pontear(pub[pub.sistema == "COICOP1999"], Ponte(), log=lambda *_: None)
nat = pub[pub.sistema == "COICOP2018"]
m = p.merge(nat, on=["pais", "coicop", "data"], suffixes=("_p", "_n"))
m = m[(m.data >= "2025-02-01") & (m.data <= "2025-12-01")].dropna(subset=["var_mensal_p", "var_mensal_n"])
def stat(g):
    x, y = g.var_mensal_p.values, g.var_mensal_n.values
    c = np.corrcoef(x, y)[0, 1] if x.std() > 0 and y.std() > 0 else np.nan
    return pd.Series({"mae_pp": np.abs(x - y).mean(), "corr": c})
por_pais = m.groupby(["coicop", "pais"]).apply(stat, include_groups=False).reset_index()
v = por_pais.groupby("coicop").agg(paises=("pais", "nunique"), mae_mediano_pp=("mae_pp", "median"), corr_mediana=("corr", "median")).reset_index()
v.round(4).to_csv(R / "tabelas/ponte_validacao.csv", index=False)
print(len(v), "nós validados;", "países por nó (mediana):", int(v.paises.median()))
print(v.describe().round(3).loc[["50%", "max"]].to_string())
print(v.sort_values("mae_mediano_pp", ascending=False).head(14).round(3).to_string(index=False))
