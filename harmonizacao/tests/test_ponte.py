import numpy as np, pandas as pd, pytest
from harmonizacao.ponte import Ponte, _anual, _mensal, emendar, pontear

def toy():
    linhas = [("01.1.1.1", "01.1.1"), ("01.1.1.2", "01.1.1"),      # 1999 01.1.1 se divide em duas subclasses de 2018
              ("01.1.2.1", "01.1.2"), ("01.1.3.1", "01.1.2"),      # 1999 01.1.2 cobre duas classes de 2018
              ("02.1.1.1", "02.1.1"), ("02.1.1.1", "02.1.2")]      # fusão: duas classes de 1999 -> uma subclasse de 2018
    return Ponte(pd.DataFrame(linhas, columns=["coicop2018", "coicop1999"]))

def test_exatidao_de_nos():
    e = toy().exatos()
    assert e["01.1.1"] == frozenset({"01.1.1"}) and "01.1.1.1" not in e          # bloco inteiro dentro da classe; subclasse sozinha não
    assert "01.1.2" not in e and "01.1.3" not in e                               # classe de 1999 dividida entre duas classes de 2018
    assert e["01.1"] == frozenset({"01.1.1", "01.1.2"}) and e["01"] == e["01.1"]  # o grupo contém todos os blocos
    assert e["02.1.1.1"] == frozenset({"02.1.1", "02.1.2"})                      # fusão n:1

def test_tabela_real_ao_menos_as_82_classes():
    p = Ponte(); e = p.exatos()
    assert sum(n.count(".") == 2 for n in e) == 82 and sum(n.count(".") == 0 for n in e) >= 3
    assert all(len(v) >= 1 for v in e.values())

def test_anual_encadeia_com_pesos_do_ano():
    d = pd.date_range("2019-12-01", periods=13, freq="MS")                       # dez/2019 .. dez/2020
    I = pd.DataFrame({"a": 100 * 1.01 ** np.arange(13), "b": 100.0}, index=d)
    W = pd.DataFrame({"a": 50.0, "b": 50.0}, index=d)
    r = _anual(I, W)
    assert r[pd.Timestamp("2020-12-01")] == pytest.approx(100 * (0.5 * 1.01 ** 12 + 0.5))

def test_mensal_e_media_ponderada():
    d = pd.date_range("2020-01-01", periods=2, freq="MS")
    V = pd.DataFrame({"a": [2.0, 2.0], "b": [0.0, 0.0]}, index=d); W = pd.DataFrame({"a": 25.0, "b": 75.0}, index=d)
    assert _mensal(V, W).iloc[0] == pytest.approx(100.5)

def _pub(cod, n=14, sistema="COICOP1999", fonte="Eurostat", origem="publicado"):
    d = pd.date_range("2019-12-01", periods=n, freq="MS")
    return pd.DataFrame({"pais": "ESP", "sistema": sistema, "coicop": cod, "data": d, "indice": 100 * 1.01 ** np.arange(n), "var_mensal": 1.0,
                         "var_12m": np.nan, "peso_pct": 10.0, "n_componentes": np.nan, "cobertura_pct": np.nan, "base_indice": "2020=100", "origem": origem, "fonte": fonte})

def test_pontear_renomeia_classe_1_para_1_sem_perder_valores():
    r = pontear(_pub("01.1.1"), toy(), log=lambda *_: None)
    assert set(r.coicop) == {"01.1.1"} and r.sistema.eq("COICOP2018").all() and r.origem.eq("ponte").all() and r.fonte.eq("Eurostat+ponte").all()
    a = _pub("01.1.1").set_index("data").indice; b = r.set_index("data").indice
    razao = (b / a).to_numpy(); assert np.allclose(razao, razao[0])                # só reescala (mesma dinâmica)

def test_pontear_nao_inventa_no_sem_todas_as_classes():
    assert pontear(_pub("02.1.1"), toy(), log=lambda *_: None).empty              # fusão exige 02.1.1 E 02.1.2

def test_emendar_usa_ponte_antes_e_nativo_depois():
    ponteado = _pub("01.1.1", n=24, sistema="COICOP2018", fonte="Eurostat+ponte", origem="ponte")
    nat = _pub("01.1.1", n=24, sistema="COICOP2018").iloc[12:].copy()
    nat["indice"] = nat.indice * 0.5; nat["base_indice"] = "nativa"                # outra base
    r = emendar(nat, ponteado).set_index("data")
    assert r.origem.eq("ponte+nativo").all() and len(r) == 24
    assert (r.var_mensal.dropna().round(6) == 1.0).all()                          # sem quebra na emenda
