"""Leitura/gravação em parquet com upsert por chave (coleta nova substitui a antiga)."""
from pathlib import Path
import pandas as pd
from .esquema import TABELAS, validar
RAIZ = Path(__file__).resolve().parents[2]
DADOS = RAIZ / "dados"; MAPS = RAIZ / "mapeamentos"

def caminho(nome, camada="curado"): return DADOS / camada / f"{nome}.parquet"

def ler(nome, camada="curado"):
    p = caminho(nome, camada)
    return pd.read_parquet(p) if p.exists() else pd.DataFrame(columns=TABELAS[nome]["cols"])

def gravar(nome, novo, camada="curado"):
    """Upsert: linhas novas substituem as de mesma chave; o resto é preservado."""
    novo = validar(nome, novo); chave = TABELAS[nome]["chave"]; antigo = ler(nome, camada)
    if len(antigo):
        m = antigo.merge(novo[chave].drop_duplicates(), on=chave, how="left", indicator=True)
        antigo = antigo[(m["_merge"] == "left_only").values]
    out = pd.concat([antigo, novo], ignore_index=True).sort_values(chave).reset_index(drop=True)
    p = caminho(nome, camada); p.parent.mkdir(parents=True, exist_ok=True); out.to_parquet(p, index=False)
    return len(novo), len(out)
