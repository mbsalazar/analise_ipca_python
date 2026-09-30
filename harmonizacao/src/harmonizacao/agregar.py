"""Núcleo do método. Duas operações:
 1. derivar(): agrega componentes nacionais em nós COICOP com pesos (regra validada contra o IBGE: variação do mês t
    ponderada pelo peso do mês t; erro máx. 0,008 p.p. ao reproduzir grupos do IPCA a partir dos subitens).
 2. publicado(): põe séries já em COICOP na mesma forma (base comum, variações, pesos)."""
import numpy as np, pandas as pd
from .coicop import ancestrais

BASE_ANO = 2020          # base comum: média de BASE_ANO = 100 (exige 12 meses)
PRIORIDADE = {"derivado": 0, "Eurostat": 1, "BLS": 2, "IBGE/SIDRA 7060": 0, "OCDE": 3}

def _encadear(var: pd.Series) -> pd.Series:
    """var em % (índice de datas mensais) -> índice com base 100 no mês anterior ao primeiro."""
    return 100 * (1 + var / 100).cumprod()

def rebasear(idx: pd.Series) -> pd.Series:
    """idx indexado por data. Base comum = média de BASE_ANO; NaN se o ano-base não tem os 12 meses."""
    b = idx[idx.index.year == BASE_ANO]
    return idx / b.mean() * 100 if b.notna().sum() == 12 else idx * np.nan

def _var12(idx: pd.Series) -> pd.Series:
    ant = idx.copy(); ant.index = ant.index + pd.DateOffset(months=12)
    return (idx / ant.reindex(idx.index) - 1) * 100

def _finalizar(g: pd.DataFrame) -> pd.DataFrame:
    """g: uma série (data, indice bruto encadeado ou publicado)."""
    g = g.sort_values("data").set_index("data"); ix = rebasear(g["indice"]); g["base_indice"] = f"{BASE_ANO}=100"
    if ix.isna().all(): ix = g["indice"]; g["base_indice"] = "nativa"       # sem os 12 meses do ano-base: mantém a base da fonte, declarada
    prev = ix.copy(); prev.index = prev.index + pd.DateOffset(months=1)
    g["indice"] = ix; g["var_mensal"] = (ix / prev.reindex(ix.index) - 1) * 100; g["var_12m"] = _var12(ix)
    return g.reset_index()

def derivar(series, pesos, mapa, folhas, pais, sistema_coicop, fonte) -> pd.DataFrame:
    """series: cod_local,data,var_mensal | pesos: cod_local,data,peso (pct) | mapa: cod_local,coicop,parcela | folhas: códigos sem filhos."""
    f = set(folhas)
    d = (series[series.cod_local.isin(f)][["cod_local", "data", "var_mensal"]]
         .merge(pesos[pesos.cod_local.isin(f)][["cod_local", "data", "peso"]], on=["cod_local", "data"])
         .merge(mapa[["cod_local", "coicop", "parcela"]], on="cod_local"))
    d["w"] = d.peso * d.parcela
    d["no"] = d.coicop.map(lambda c: [c] + ancestrais(c)); d = d.explode("no")
    d["wv"] = d.w * d.var_mensal
    g = d.groupby(["no", "data"]).agg(wv=("wv", "sum"), w=("w", "sum"), n=("cod_local", "nunique")).reset_index()
    g["var"] = g.wv / g.w
    tot = pesos[pesos.cod_local.isin(f)].groupby("data").peso.sum().rename("peso_total")
    mapeado = d.drop_duplicates(["cod_local", "data", "coicop"]).groupby("data").w.sum().rename("peso_mapeado")
    cob = (mapeado / tot * 100).rename("cobertura_pct")
    out = []
    for no, s in g.groupby("no"):
        s = s.sort_values("data").set_index("data"); r = pd.DataFrame({"data": s.index, "indice": _encadear(s["var"]).values})
        r = _finalizar(r); r["coicop"] = no
        r["var_mensal"] = r.data.map(s["var"])            # variação ponderada direta (não recalculada do índice arredondado)
        r = r.merge(s[["w", "n"]].rename(columns={"w": "peso_pct", "n": "n_componentes"}), left_on="data", right_index=True)
        out.append(r)
    r = pd.concat(out, ignore_index=True).merge(cob, left_on="data", right_index=True, how="left")
    r["peso_pct"] = r.peso_pct  # soma dos pesos das folhas mapeadas, em % do índice nacional
    return r.assign(pais=pais, sistema=sistema_coicop, origem="derivado", fonte=fonte)

def publicado(series, pesos=None) -> pd.DataFrame:
    """series: pais,sistema_local,cod_local,data,indice,fonte (indice != NaN)."""
    s = series.dropna(subset=["indice"]); out = []
    for (p, sis, cod, fonte), g in s.groupby(["pais", "sistema_local", "cod_local", "fonte"]):
        r = _finalizar(g[["data", "indice"]].copy()); out.append(r.assign(pais=p, sistema=sis, coicop=cod, fonte=fonte))
    r = pd.concat(out, ignore_index=True)
    r["peso_pct"] = np.nan; r["n_componentes"] = np.nan; r["cobertura_pct"] = np.nan; r["origem"] = "publicado"
    if pesos is not None and len(pesos):
        w = pesos.assign(ano=pesos.data.dt.year, peso_pct=np.where(pesos.escala == "permil", pesos.peso / 10, pesos.peso))
        w = w.rename(columns={"sistema_local": "sistema", "cod_local": "coicop"})[["pais", "sistema", "coicop", "fonte", "ano", "peso_pct"]]
        r["ano"] = r.data.dt.year; r = r.drop(columns="peso_pct").merge(w, on=["pais", "sistema", "coicop", "fonte", "ano"], how="left").drop(columns="ano")
        r["peso_pct"] = r.peso_pct.astype(float)
    return r

def escolher_fonte(df: pd.DataFrame) -> pd.DataFrame:
    """Uma fonte por série (pais, sistema, coicop): a mais recente; empate: a mais longa; empate: PRIORIDADE."""
    r = df.dropna(subset=["indice"]).groupby(["pais", "sistema", "coicop", "fonte"]).agg(fim=("data", "max"), n=("data", "size")).reset_index()
    r["prio"] = r.fonte.map(PRIORIDADE).fillna(9)
    win = r.sort_values(["pais", "sistema", "coicop", "fim", "n", "prio"], ascending=[True, True, True, False, False, True]).drop_duplicates(["pais", "sistema", "coicop"])
    return df.merge(win[["pais", "sistema", "coicop", "fonte"]], on=["pais", "sistema", "coicop", "fonte"])
