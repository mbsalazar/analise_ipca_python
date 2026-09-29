"""Esquema das tabelas (parquet). Chaves de upsert definem o que uma nova coleta substitui."""
import pandas as pd

TABELAS = {
    # cesta como cada país publica (hierarquia nacional)
    "item_nacional": dict(chave=["pais", "sistema_local", "cod_local"],
                          cols=["pais", "sistema_local", "cod_local", "nome", "nivel", "cod_pai"]),
    # série como publicada: índice e/ou variação mensal, sempre com a base declarada
    "serie_nacional": dict(chave=["pais", "sistema_local", "cod_local", "data", "fonte"],
                           cols=["pais", "sistema_local", "cod_local", "data", "indice", "var_mensal", "base", "fonte"]),
    # pesos como publicados (escala declarada: 'pct' soma 100, 'permil' soma 1000)
    "peso_nacional": dict(chave=["pais", "sistema_local", "cod_local", "data", "fonte"],
                          cols=["pais", "sistema_local", "cod_local", "data", "peso", "escala", "fonte"]),
    # resultado: séries por nó COICOP, publicadas pela fonte ou derivadas por nós
    "ipc_harmonizado": dict(chave=["pais", "sistema", "coicop", "data"],
                            cols=["pais", "sistema", "coicop", "data", "indice", "var_mensal", "var_12m", "peso_pct",
                                  "n_componentes", "cobertura_pct", "origem", "fonte"]),
}
MAPEAMENTO_COLS = ["pais", "sistema_local", "cod_local", "sistema_coicop", "coicop", "tipo", "parcela", "metodo", "confianca", "revisado"]

def validar(nome: str, df: pd.DataFrame) -> pd.DataFrame:
    t = TABELAS[nome]; falta = [c for c in t["cols"] if c not in df.columns]
    if falta: raise ValueError(f"{nome}: colunas ausentes {falta}")
    df = df[t["cols"]]
    dup = df.duplicated(t["chave"]).sum()
    if dup: raise ValueError(f"{nome}: {dup} linhas duplicadas na chave {t['chave']}")
    return df
