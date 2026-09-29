import numpy as np, pandas as pd, pytest
from harmonizacao import armazem as A
from harmonizacao.agregar import derivar, escolher_fonte, publicado, rebasear
from harmonizacao.coicop import ancestrais, nivel, pontuar
from harmonizacao.conectores.ibge_sidra import _cod, normalizar, pai
from harmonizacao.esquema import validar
from harmonizacao.paises import iso3

def test_coicop_codigos():
    assert pontuar("CP0111") == "01.1.1" and pontuar("CP00") == "00" and pontuar("FOOD") is None
    assert ancestrais("01.1.2") == ["01.1", "01", "00"] and nivel("01.1.2") == 3 and nivel("00") == 0

def test_paises():
    assert iso3("EL") == "GRC" and iso3("UK") == "GBR" and iso3("ES") == "ESP" and iso3("EA20") is None

def test_sidra_hierarquia():
    assert pai("1101002") == "1101" and pai("1101") == "11" and pai("11") == "1" and pai("1") == "0" and pai("0") is None
    assert _cod("Índice geral") == "0" and _cod("1101002.Arroz") == "1101002"

def _meses(n=14): return pd.date_range("2019-12-01", periods=n, freq="MS")

def test_derivar_media_ponderada_e_total():
    d = pd.date_range("2020-01-01", periods=12, freq="MS")            # 12 meses de 2020 = base comum
    ser = pd.DataFrame([(c, t, v) for c, v in {"a": 2.0, "b": 0.0}.items() for t in d], columns=["cod_local", "data", "var_mensal"])
    pes = pd.DataFrame([(c, t, w) for c, w in {"a": 25.0, "b": 75.0}.items() for t in d], columns=["cod_local", "data", "peso"])
    mapa = pd.DataFrame({"cod_local": ["a", "b"], "coicop": ["01.1.1", "01.1.2"], "parcela": 1.0})
    r = derivar(ser, pes, mapa, ["a", "b"], "XXX", "COICOP1999", "teste")
    tot = r[r.coicop == "00"].sort_values("data")
    assert tot.var_mensal.round(9).eq(0.5).all()                       # (25*2 + 75*0)/100, inclusive no 1º mês
    assert tot.indice.mean() == pytest.approx(100)                     # base 2020=100
    assert set(r.coicop) == {"01.1.1", "01.1.2", "01.1", "01", "00"}
    assert (tot.cobertura_pct == 100).all() and (tot.n_componentes == 2).all()

def test_derivar_cobertura_parcial():
    d = _meses(3)[1:]
    ser = pd.DataFrame([(c, t, 1.0) for c in "ab" for t in d], columns=["cod_local", "data", "var_mensal"])
    pes = pd.DataFrame([(c, t, w) for c, w in {"a": 30.0, "b": 70.0}.items() for t in d], columns=["cod_local", "data", "peso"])
    mapa = pd.DataFrame({"cod_local": ["a"], "coicop": ["01.1.1"], "parcela": 1.0})   # 'b' sem de-para
    r = derivar(ser, pes, mapa, ["a", "b"], "XXX", "COICOP1999", "t")
    assert r.cobertura_pct.round(6).unique().tolist() == [30.0]

def test_rebasear_exige_12_meses():
    idx = pd.Series(np.arange(1, 25, dtype=float) + 100, index=pd.date_range("2019-01-01", periods=24, freq="MS"))
    assert rebasear(idx)[idx.index.year == 2020].mean() == pytest.approx(100)
    assert rebasear(idx.iloc[:20]).isna().all()      # 2020 incompleto -> não inventa base

def test_publicado_var12_e_peso_eurostat():
    t = pd.date_range("2019-01-01", periods=36, freq="MS")
    s = pd.DataFrame({"pais": "ESP", "sistema_local": "COICOP1999", "cod_local": "01", "data": t, "indice": 100 * 1.01 ** np.arange(36), "fonte": "Eurostat"})
    w = pd.DataFrame({"pais": "ESP", "sistema_local": "COICOP1999", "cod_local": "01", "data": pd.to_datetime(["2021-01-01"]), "peso": 200.0, "escala": "permil", "fonte": "Eurostat"})
    r = publicado(s, w).set_index("data")
    assert r.loc["2021-06-01", "var_12m"] == pytest.approx((1.01 ** 12 - 1) * 100) and r.loc["2021-06-01", "peso_pct"] == 20.0
    assert r.loc["2020-06-01", "peso_pct"] != r.loc["2020-06-01", "peso_pct"]      # sem peso naquele ano: NaN

def test_escolher_fonte_mais_recente():
    def mk(f, n): return pd.DataFrame({"pais": "X", "sistema": "S", "coicop": "01", "fonte": f, "data": pd.date_range("2020-01-01", periods=n, freq="MS"), "indice": 1.0})
    out = escolher_fonte(pd.concat([mk("Eurostat", 12), mk("OCDE", 20)]))
    assert out.fonte.unique().tolist() == ["OCDE"]

def test_upsert_substitui_chave(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "DADOS", tmp_path)
    base = dict(pais="BRA", sistema_local="S", cod_local="1", data=pd.Timestamp("2020-01-01"), escala="pct", fonte="f")
    A.gravar("peso_nacional", pd.DataFrame([{**base, "peso": 1.0}, {**base, "data": pd.Timestamp("2020-02-01"), "peso": 2.0}]))
    A.gravar("peso_nacional", pd.DataFrame([{**base, "peso": 9.0}]))               # revisão de jan/2020
    r = A.ler("peso_nacional").sort_values("data")
    assert r.peso.tolist() == [9.0, 2.0]

def test_validar_rejeita_duplicata():
    b = dict(pais="B", sistema_local="S", cod_local="1", data=pd.Timestamp("2020-01-01"), escala="pct", fonte="f", peso=1.0)
    with pytest.raises(ValueError): validar("peso_nacional", pd.DataFrame([b, b]))

def test_mapa_brasil_consistente():
    m = pd.read_csv(A.MAPS / "BRA.csv", dtype=str)
    assert m.cod_local.is_unique and m.cod_local.str.len().eq(7).all()          # 1 classe por subitem, sem dupla contagem
    assert m.parcela.astype(float).eq(1).all()

def test_ocde_total_vira_00():
    from harmonizacao.conectores import ocde
    csv = "REF_AREA,EXPENDITURE,TIME_PERIOD,OBS_VALUE,BASE_PER\nCHL,_T,2026-08,120.5,2015\nCHL,CP01,2026-08,130.0,2015\nCHL,FOOD,2026-08,1.0,2015\n"
    ocde.get = lambda url, **kw: type("R", (), {"text": csv})()
    r = ocde.Ocde().coletar("2026-01").series
    assert set(r[r.sistema_local == "COICOP2018"].cod_local) == {"00", "01"}      # 'FOOD' (agregado) fica de fora
