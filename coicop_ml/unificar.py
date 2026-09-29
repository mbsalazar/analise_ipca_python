"""Empilha EUA (BLS), Eurostat e OCDE num único arquivo com país em ISO-3 e uma escolha de fonte por série."""
import pandas as pd, pycountry
r = lambda f: pd.read_csv(f, dtype={"coicop": str}, parse_dates=["data"])
# --- correspondência oficial ONU 2018 <-> 1999
c = pd.read_excel("fontes/coicop2018_1999_correspondencia.xlsx", sheet_name="Correspondence 2018-1999", dtype=str)
c.columns = ["coicop2018", "titulo2018", "coicop1999", "titulo1999", "nota"]
c.to_csv("dados/coicop_correspondencia_2018_1999.csv", index=False)
# --- países: Eurostat usa ISO-2 com exceções (EL=Grécia, UK=Reino Unido, XK=Kosovo)
excecoes = {"EL": "GRC", "UK": "GBR", "XK": "XKX"}
iso3 = lambda x: excecoes.get(x) or (pycountry.countries.get(alpha_2=x).alpha_3 if len(x) == 2 and pycountry.countries.get(alpha_2=x) else x)
es = r("dados/eurostat_indices.csv.gz"); es["pais"] = es.pais.map(iso3)
es = es[es.pais != "USA"]                       # o HICP traz só agregados dos EUA
ocde = pd.concat([r("dados/ocde_indices_COICOP2018.csv.gz"), r("dados/ocde_indices_COICOP1999.csv.gz")])
ocde = ocde[~ocde.pais.isin(["EA", "EA20", "EU27_2020", "OECD", "OECDE", "G7", "G20"])]
# --- EUA (BLS): '1.1.1' -> '01.1.1'; descarta agrupamentos ('4.42 + 4.43')
us = r("dados/eua_indices.csv") if False else pd.read_csv("dados/eua_indices.csv", dtype=str, parse_dates=["data"])
us = us[~us.cod_origem.str.contains(r"[+A-Za-z]")].copy()
us["indice"] = us.indice.astype(float)
us["coicop"] = us.cod_origem.map(lambda s: ".".join([s.split(".")[0].zfill(2)] + ([d for d in s.split(".")[1]] if "." in s and len(s.split(".")[1]) > 0 else [])) if "." in s else s.zfill(2))
us = pd.DataFrame({"fonte": "BLS", "pais": "USA", "sistema": "COICOP1999", "coicop": us.coicop, "data": us.data, "indice": us.indice})
todos = pd.concat([es, ocde[es.columns], us], ignore_index=True)
todos["nivel"] = todos.coicop.str.count(r"\.") + 1
# --- prioridade de fonte por (país, sistema, coicop): quem tem mais pontos ganha; empate: Eurostat > BLS > OCDE
n = todos.groupby(["pais", "sistema", "coicop", "fonte"]).size().rename("n").reset_index()
n["prio"] = n.fonte.map({"Eurostat": 0, "BLS": 1, "OCDE": 2})
melhor = n.sort_values(["pais", "sistema", "coicop", "n", "prio"], ascending=[True, True, True, False, True]).drop_duplicates(["pais", "sistema", "coicop"])[["pais", "sistema", "coicop", "fonte"]]
final = todos.merge(melhor, on=["pais", "sistema", "coicop", "fonte"])
final.drop(columns="nivel").to_csv("dados/indices_unificado.csv.gz", index=False)
print("linhas", len(final), "| países", final.pais.nunique(), "| séries", final.groupby(["pais","sistema","coicop"]).ngroups)
print(final.groupby(["sistema", "fonte"]).pais.nunique())
print("USA amostra:", sorted(final[final.pais == "USA"].coicop.unique())[:14])
