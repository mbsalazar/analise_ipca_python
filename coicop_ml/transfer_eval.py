"""Transferência entre países com o baseline TF-IDF (PT<->ES têm muitos cognatos). Treina num país, testa no outro,
só nas classes COICOP presentes no treino (senão o erro seria inevitável)."""
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
br = pd.read_csv("brasil_subitens_rotulados.csv"); cl = pd.read_csv("chile_produtos_rotulados.csv")
txt = lambda d: (d.subitem + " | " + d.item).str.lower()
def run(tr, te, nome):
    cobertos = te.coicop.isin(set(tr.coicop)); t = te[cobertos]
    m = make_pipeline(TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True), LogisticRegression(C=20, max_iter=3000))
    m.fit(txt(tr), tr.coicop); p = m.predict(txt(t))
    a3 = (p == t.coicop).mean(); a2 = (pd.Series(p).str[:2].values == t.coicop.str[:2].values).mean()
    print(f"{nome}: n={len(t)}/{len(te)} (classes presentes no treino) | classe 3 níveis {a3:.1%} | divisão {a2:.1%}")
run(br, cl, "treina Brasil -> testa Chile ")
run(cl, br, "treina Chile  -> testa Brasil ")
print("classes só no Chile :", sorted(set(cl.coicop) - set(br.coicop)))
print("classes só no Brasil:", sorted(set(br.coicop) - set(cl.coicop)))
print(cl.nivel_gabarito.value_counts().sort_index().to_dict(), "(nível do gabarito: 1=div .. 4=subclasse)")
