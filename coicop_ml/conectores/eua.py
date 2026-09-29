"""EUA: o BLS já publica o CPI em COICOP (série de pesquisa R-COICOP, dez/2013=100). Não precisa classificar."""
import openpyxl, pandas as pd
def carregar(path="fontes/r-coicop-data.xlsx"):
    rows = list(openpyxl.load_workbook(path, read_only=True, data_only=True)["Indexes"].iter_rows(values_only=True))
    hdr = rows[2]; datas = pd.to_datetime([h[1:] for h in hdr[2:]], format="%Y%m")
    recs = [(str(r[0]), r[1].strip(), d, v) for r in rows[3:] if r[0] is not None and r[1]
            for d, v in zip(datas, r[2:]) if isinstance(v, (int, float))]
    df = pd.DataFrame(recs, columns=["cod_origem", "descricao", "data", "indice"]); df.insert(0, "pais", "EUA")
    return df
if __name__ == "__main__":
    df = carregar(); df.to_csv("dados/eua_indices.csv", index=False)
    print(df.cod_origem.nunique(), "séries |", df.data.min().date(), "a", df.data.max().date())
    print(sorted(df.cod_origem.unique(), key=lambda c: [float(x) if x.replace('.','').isdigit() else 999 for x in c.split('.')][:1])[:60])
