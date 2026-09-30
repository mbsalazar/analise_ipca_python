"""Ponte COICOP 1999 -> 2018 com base na tabela oficial da ONU (UNSD).

A tabela liga subclasses de 2018 (4 níveis) a classes de 1999 (3 níveis). Ligações formam um grafo; cada componente
conexa é um bloco com o MESMO conteúdo nas duas versões. Consequência:
  * um nó N de 2018 é reconstruível EXATAMENTE de séries de 1999 se todas as suas subclasses pertencem a blocos inteiros
    contidos em N (então N = agregação das classes de 1999 desses blocos);
  * o resto (a maior parte das divisões e grupos) NÃO é reconstruível: um bloco emaranhado une 55 classes de 1999
    e 171 subclasses de 2018. Nesses casos a saída é fonte nativa em 2018 ou classificar a cesta direto em 2018.
"""
import networkx as nx, numpy as np, pandas as pd
from . import armazem as A
from .agregar import _finalizar

class Ponte:
    def __init__(self, tabela: pd.DataFrame | None = None):
        c = tabela if tabela is not None else pd.read_csv(A.TABELAS_REF / "coicop_correspondencia_2018_1999.csv", dtype=str)
        c = c[c.coicop2018.str.count(r"\.") == 3]                       # subclasses de 2018
        G = nx.Graph()
        for r in c.itertuples():
            G.add_node("18:" + r.coicop2018)
            if r.coicop1999 != "-": G.add_edge("18:" + r.coicop2018, "99:" + r.coicop1999)
        self.blocos = []                                                # [(subclasses2018, classes1999)]
        for k in nx.connected_components(G):
            self.blocos.append(({n[3:] for n in k if n[:2] == "18"}, {n[3:] for n in k if n[:2] == "99"}))
        self._bloco18 = {s: i for i, (s18, _) in enumerate(self.blocos) for s in s18}
        self.sub18 = sorted(self._bloco18)

    def _filhos(self, n): return [s for s in self.sub18 if s == n or s.startswith(n + ".")]

    def requer(self, no: str):
        """Classes de 1999 que reconstroem exatamente o nó de 2018; None se não for exato."""
        f = set(self._filhos(no))
        if not f: return None
        blocos = {self._bloco18[s] for s in f}
        if any(not self.blocos[b][1] or not self.blocos[b][0] <= f for b in blocos): return None
        return frozenset().union(*[self.blocos[b][1] for b in blocos])

    def exatos(self):
        nos = {".".join(s.split(".")[:i]) for s in self.sub18 for i in range(1, 5)}
        return {n: r for n in sorted(nos) if (r := self.requer(n)) is not None}

    def candidatos_2018(self, cod99: str):
        """Subclasses de 2018 que compartilham conteúdo com uma classe de 1999 (apoio ao de-para direto em 2018)."""
        return sorted(s for s, b in self._bloco18.items() if cod99 in self.blocos[b][1])

def _anual(I: pd.DataFrame, W: pd.DataFrame) -> pd.Series:
    """Encadeamento anual (método HICP): no ano y, índice = nível de dez(y-1) x Σ w·(I_t/I_dez(y-1)) / Σ w. I, W: data x classe."""
    out = pd.Series(np.nan, index=I.index); nivel = 100.0; ini = True
    for y in sorted(set(I.index.year)):
        meses = I.index[I.index.year == y]; dez = pd.Timestamp(y - 1, 12, 1)
        base = dez if dez in I.index else meses[0]
        if base not in I.index or I.loc[base].isna().any(): continue
        if ini or dez not in I.index: nivel = 100.0 if ini else nivel
        ini = False
        for t in meses:
            w = W.loc[t]; ok = w.notna() & I.loc[t].notna()
            if ok.sum() < len(w): continue
            out[t] = nivel * (w * I.loc[t] / I.loc[base]).sum() / w.sum()
        if dez not in I.index: nivel = out.get(meses[0], nivel)
        else: nivel = out.get(pd.Timestamp(y, 12, 1), np.nan)
        if np.isnan(nivel): break
    return out

def _mensal(V: pd.DataFrame, W: pd.DataFrame) -> pd.Series:
    """Pesos mensais: var(t) = Σ w·v / Σ w; índice encadeado (base 100 no mês anterior ao primeiro)."""
    ok = V.notna() & W.notna(); v = (V.where(ok) * W.where(ok)).sum(axis=1, min_count=1) / W.where(ok).sum(axis=1)
    return 100 * (1 + v / 100).cumprod()

def pontear(pub1999: pd.DataFrame, ponte: Ponte, log=print) -> pd.DataFrame:
    """pub1999: linhas de ipc_harmonizado (sistema COICOP1999) já com base comum e pesos. Devolve linhas COICOP2018 (origem 'ponte').
    Só séries PUBLICADAS pela fonte entram: a tabela da ONU assume o conteúdo oficial de cada classe de 1999, e isso foi validado
    contra o nativo de 2018 do Eurostat (45 nós, até 36 países, erro mensal mediano <= 0,007 p.p.). Séries DERIVADAS de uma cesta
    nacional por de-para nosso (origem 'derivado') ficam de fora: o de-para do Brasil usa códigos de 1999 com conteúdo diferente do
    oficial (ex.: 12.1.2 com produtos de cuidado pessoal, 10.1.0 com todos os níveis de ensino, 01.1.4 com frango)."""
    exatos = ponte.exatos(); out = []; pulados = 0
    pub1999 = pub1999[pub1999.origem == "publicado"]
    cls = pub1999[pub1999.coicop.str.count(r"\.") == 2]
    for (pais, fonte, origem), g in cls.groupby(["pais", "fonte", "origem"]):
        I = g.pivot(index="data", columns="coicop", values="indice").sort_index()
        Wp = g.pivot(index="data", columns="coicop", values="peso_pct").reindex(I.index)
        V = g.pivot(index="data", columns="coicop", values="var_mensal").reindex(I.index)
        disp = set(I.columns[I.notna().any()])
        for no, req in exatos.items():
            if not req <= disp: continue
            cols = sorted(req)
            if len(cols) == 1: idx = I[cols[0]]; peso = Wp[cols[0]]
            elif Wp[cols].isna().all().any(): pulados += 1; continue          # classe sem nenhum peso: não agrega
            else:
                idx = _mensal(V[cols], Wp[cols]) if origem == "derivado" else _anual(I[cols], Wp[cols])
                peso = Wp[cols].sum(axis=1, min_count=len(cols))
            if idx.notna().sum() < 2: pulados += 1; continue
            r = _finalizar(pd.DataFrame({"data": idx.index, "indice": idx.values}).dropna())
            r = r.merge(peso.rename("peso_pct"), left_on="data", right_index=True, how="left")
            out.append(r.assign(pais=pais, sistema="COICOP2018", coicop=no, n_componentes=len(cols), cobertura_pct=np.nan,
                                origem="ponte", fonte=f"{fonte}+ponte"))
    if pulados: log(f"  ponte: {pulados} nós exatos pulados (sem pesos ou séries insuficientes)")
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()

def emendar(nativo: pd.DataFrame, ponteado: pd.DataFrame, min_sobreposicao=6) -> pd.DataFrame:
    """Nativo 2018 curto (base 'nativa') + ponte com histórico: reescala o nativo pela razão média na sobreposição e
    usa a ponte antes dele. Ambos com colunas de ipc_harmonizado; o nativo deve estar na base da fonte ('nativa')."""
    out = []
    for (pais, no), n in nativo[nativo.base_indice == "nativa"].groupby(["pais", "coicop"]):
        p = ponteado[(ponteado.pais == pais) & (ponteado.coicop == no)]
        if p.empty: continue
        n = n.set_index("data").indice; pi = p.groupby("data").indice.first()
        so = n.index.intersection(pi.index)
        if len(so) < min_sobreposicao: continue
        k = (pi[so] / n[so]).mean(); junto = pd.concat([pi[pi.index < n.index.min()], n * k]).sort_index()
        r = _finalizar(pd.DataFrame({"data": junto.index, "indice": junto.values}))
        r["peso_pct"] = np.nan; r["n_componentes"] = np.nan; r["cobertura_pct"] = np.nan
        f = p.fonte.iloc[0].replace("+ponte", "")
        out.append(r.assign(pais=pais, sistema="COICOP2018", coicop=no, origem="ponte+nativo", fonte=f"{f}+ponte+nativo"))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()
