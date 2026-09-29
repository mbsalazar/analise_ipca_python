"""Brasil: IPCA (IBGE/SIDRA tabela 7060, desde jan/2020). Variação mensal (v63) e peso mensal (v66) de 457 categorias:
geral, grupo, subgrupo, item e subitem. O índice é reconstruído por encadeamento a partir das variações (base dez/2019=100)."""
import pandas as pd
from ..http import get
from .base import Conector, Resultado
API = "https://apisidra.ibge.gov.br/values/t/7060/n1/all/v/63,66/p/{p}/c315/all"
LIMITE = 50000          # valores por pedido; 457 categorias x 2 variáveis = 914 por mês
MESES_POR_PEDIDO = 40

def _periodos(desde: str | None, ate: str):
    ini = pd.Period(desde or "2020-01", "M"); fim = pd.Period(ate, "M")
    todos = pd.period_range(ini, fim, freq="M")
    for i in range(0, len(todos), MESES_POR_PEDIDO):
        b = todos[i:i + MESES_POR_PEDIDO]; yield f"{b[0].strftime('%Y%m')}-{b[-1].strftime('%Y%m')}"

def ultimo_periodo_publicado():
    j = get("https://servicodados.ibge.gov.br/api/v3/agregados/7060/periodos").json()
    return pd.Period(max(x["id"] for x in j), "M").strftime("%Y-%m")

def _cod(nome: str) -> str:
    return "0" if nome.startswith("Índice geral") else nome.split(".")[0]

def nivel(cod: str) -> int:   # 0 geral, 1 grupo, 2 subgrupo, 4 item, 7 subitem
    return {1: 1, 2: 2, 4: 3, 7: 4}.get(len(cod), 0) if cod != "0" else 0

def pai(cod: str):
    return None if cod == "0" else {1: "0", 2: cod[:1], 4: cod[:2], 7: cod[:4]}[len(cod)]

def baixar_bruto(desde=None):
    partes = []
    for p in _periodos(desde, ultimo_periodo_publicado()):
        j = get(API.format(p=p)).json()
        if not isinstance(j, list): raise RuntimeError(f"SIDRA: {j}")
        partes.append(pd.DataFrame(j[1:]))
    return pd.concat(partes, ignore_index=True)

def normalizar(bruto: pd.DataFrame) -> Resultado:
    d = bruto.rename(columns={"D2C": "var", "D3C": "per", "D4N": "nome", "V": "v"})[["var", "per", "nome", "v"]].copy()
    d["cod_local"] = d.nome.map(_cod); d["v"] = pd.to_numeric(d.v, errors="coerce")
    d["data"] = pd.to_datetime(d.per, format="%Y%m")
    base = dict(pais="BRA", sistema_local="IPCA_SNIPC")
    itens = d.drop_duplicates("cod_local")[["cod_local", "nome"]].copy()
    itens["nome"] = itens.nome.str.replace(r"^\d+\.", "", regex=True); itens["nivel"] = itens.cod_local.map(nivel)
    itens["cod_pai"] = itens.cod_local.map(pai); itens = itens.assign(**base)
    var = d[d["var"] == "63"].rename(columns={"v": "var_mensal"})[["cod_local", "data", "var_mensal"]]
    peso = d[d["var"] == "66"].rename(columns={"v": "peso"})[["cod_local", "data", "peso"]]
    series = var.assign(indice=float("nan"), base="2019-12=100 (encadeado)", fonte="IBGE/SIDRA 7060", **base)
    pesos = peso.assign(escala="pct", fonte="IBGE/SIDRA 7060", **base)
    return Resultado(itens=itens, series=series.dropna(subset=["var_mensal"]), pesos=pesos.dropna(subset=["peso"]))

class IbgeSidra(Conector):
    pais = "BRA"
    def coletar(self, desde=None) -> Resultado:
        return normalizar(baixar_bruto(desde))
