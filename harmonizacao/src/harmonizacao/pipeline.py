"""Atualização mensal: coletar -> curado (upsert) -> publicar (recalcula do curado, idempotente)."""
import pandas as pd
from . import armazem as A
from .agregar import derivar, escolher_fonte, publicado
from .conectores.bls import Bls
from .conectores.eurostat import Eurostat, Eurostat2018
from .conectores.ibge_sidra import IbgeSidra
from .conectores.ocde import Ocde
from .ponte import Ponte, emendar, pontear
from .esquema import MAPEAMENTO_COLS

FONTES = {"ibge": IbgeSidra, "eurostat": Eurostat, "eurostat2018": Eurostat2018, "ocde": Ocde, "bls": Bls}

def coletar(fontes, desde=None, log=print):
    for nome in fontes:
        log(f"[{nome}] coletando (desde={desde or 'início'}) ...")
        r = FONTES[nome]().coletar(desde)
        for tab, df in (("item_nacional", r.itens), ("serie_nacional", r.series), ("peso_nacional", r.pesos)):
            if len(df): log(f"  {tab}: +{A.gravar(tab, df)[0]:,} linhas")

def mapeamentos():
    fs = sorted(A.MAPS.glob("*.csv"))
    return pd.concat([pd.read_csv(f, dtype={"cod_local": str, "coicop": str}) for f in fs], ignore_index=True) if fs else pd.DataFrame(columns=MAPEAMENTO_COLS)

def publicar(log=print):
    itens, ser, pes, maps = (A.ler("item_nacional"), A.ler("serie_nacional"), A.ler("peso_nacional"), mapeamentos())
    partes = []
    # 1) países com de-para: derivar (séries só com variação + pesos)
    for (pais, sl, sc), m in maps.groupby(["pais", "sistema_local", "sistema_coicop"]):
        s = ser[(ser.pais == pais) & (ser.sistema_local == sl) & ser.indice.isna() & ser.var_mensal.notna()]
        if s.empty: continue
        it = itens[(itens.pais == pais) & (itens.sistema_local == sl)]
        folhas = it[~it.cod_local.isin(set(it.cod_pai.dropna()))].cod_local
        log(f"[{pais}] derivando {m.coicop.nunique()} classes COICOP de {len(folhas)} componentes ({s.fonte.iloc[0]})")
        partes.append(derivar(s, pes[(pes.pais == pais) & (pes.sistema_local == sl)], m, folhas, pais, sc, s.fonte.iloc[0]))
    # 2) fontes já em COICOP: padronizar base, variações e pesos
    pub = ser[ser.indice.notna()]
    if len(pub): partes.append(publicado(pub, pes))
    tudo = pd.concat(partes, ignore_index=True)
    # 3) ponte 1999 -> 2018: nós exatos a partir de séries de 1999; emenda o nativo 2018 curto (base 'nativa') ao histórico
    ponteado = pontear(tudo[tudo.sistema == "COICOP1999"], Ponte(), log)
    if len(ponteado):
        partes = [tudo, ponteado]
        emend = emendar(tudo[(tudo.sistema == "COICOP2018") & (tudo.origem == "publicado")], ponteado)
        if len(emend): partes.append(emend)
        log(f"  ponte: {ponteado.groupby(['pais','coicop']).ngroups:,} séries 2018 reconstruídas; {emend.groupby(['pais','coicop']).ngroups if len(emend) else 0:,} emendadas com o nativo")
        tudo = pd.concat(partes, ignore_index=True)
    final = escolher_fonte(tudo)[["pais", "sistema", "coicop", "data", "indice", "var_mensal", "var_12m", "peso_pct", "n_componentes", "cobertura_pct", "base_indice", "origem", "fonte"]]
    A.caminho("ipc_harmonizado", "publicado").parent.mkdir(parents=True, exist_ok=True)
    final.sort_values(["pais", "sistema", "coicop", "data"]).to_parquet(A.caminho("ipc_harmonizado", "publicado"), index=False)
    log(f"publicado: {len(final):,} linhas, {final.pais.nunique()} países, {final.groupby(['pais','sistema','coicop']).ngroups:,} séries")
    return final
