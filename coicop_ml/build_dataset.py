"""Lê a planilha COICOP x SNIPC (Brasil) e gera tabelas limpas + pares gabarito (subitem -> classe COICOP)."""
import re, sys
import pandas as pd, openpyxl

XLSX = sys.argv[1] if len(sys.argv) > 1 else "data_brasil.xlsx"
wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)

# --- COICOP (aba 1): nível pelo número de partes do código
coicop = []
for (_, _, lab) in wb["COICOP"].iter_rows(values_only=True):
    if not lab: continue
    m = re.match(r"^([\d./]+)\s+(.*)$", str(lab).strip())
    if m: coicop.append((m.group(1), m.group(2)))
coicop = pd.DataFrame(coicop, columns=["coicop", "coicop_desc"])
coicop["nivel"] = coicop.coicop.str.replace("/", ".").str.count(r"\.") + 1

# --- SNIPC: item (aba 2) e subitem (aba 3), com hierarquia por prefixo do código
snipc = {}
for sheet in ("BRASIL_ITEM", "BRASIL_SUB"):
    for row in wb[sheet].iter_rows(values_only=True):
        code, lab = row[1], row[2]
        if code is None or lab is None: continue
        snipc[str(code).replace(".", "")] = str(lab).strip()
sub = pd.DataFrame([(c, l) for c, l in snipc.items() if len(c) == 7], columns=["codigo", "subitem"])
sub["item_cod"] = sub.codigo.str[:4]
sub["item"] = sub.item_cod.map(snipc)
sub["grupo"] = sub.codigo.str[:2].map(snipc)
items = pd.DataFrame([(c, l) for c, l in snipc.items() if len(c) == 4], columns=["item_cod", "item"])

# --- Compatibilização (aba 4): pares (código, rótulo) a partir da coluna I
gold_rows, excl = [], set()
for row in wb["compatibilização"].iter_rows(values_only=True):
    lab = row[2]
    if not lab: continue
    cod = str(lab).split()[0]
    cells = row[8:]
    for i in range(0, len(cells) - 1, 2):
        a, b = cells[i], cells[i + 1]
        if a is None: continue
        if isinstance(a, str) and a.startswith("menos"):
            excl.add(re.findall(r"\d{7}", a)[0]); continue
        if isinstance(b, str) and str(b).startswith("menos"):
            excl.add(re.findall(r"\d{7}", b)[0]); continue
        gold_rows.append((cod, str(a)))
gold = pd.DataFrame(gold_rows, columns=["coicop", "snipc_cod"])
gold = gold[gold.snipc_cod.str.len() >= 4]          # descarta grupos (1 e 2 dígitos)

# --- expande itens (4 díg.) para os subitens que eles contêm
rows = []
for cop, cod in gold.itertuples(index=False):
    if len(cod) == 7:
        rows.append((cod, cop))
    elif len(cod) == 4:
        for s in sub.codigo[sub.item_cod == cod]:
            if s not in excl: rows.append((s, cop))
lab = pd.DataFrame(rows, columns=["codigo", "coicop"]).drop_duplicates()
dups = lab.groupby("codigo").coicop.nunique()
print("subitens com >1 classe COICOP:", (dups > 1).sum())
sub = sub.merge(lab, on="codigo", how="left").merge(coicop[["coicop", "coicop_desc"]], on="coicop", how="left")
sub["coicop"] = sub.coicop.fillna("SEM_CORRESPONDENCIA")
print("subitens:", len(sub), "| mapeados:", (sub.coicop != "SEM_CORRESPONDENCIA").sum(),
      "| classes COICOP usadas:", sub.coicop[sub.coicop != "SEM_CORRESPONDENCIA"].nunique(), "de", (coicop.nivel >= 3).sum())
coicop.to_csv("coicop.csv", index=False); sub.to_csv("brasil_subitens_rotulados.csv", index=False)
print(sub.coicop.value_counts().head(8))
