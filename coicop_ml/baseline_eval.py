"""Baseline supervisionado (TF-IDF + regressão logística). CV agrupada por item SNIPC: o modelo nunca vê
irmãos do subitem testado, o que simula 'item novo'. Mede o teto do que dá pra aprender só com o Brasil."""
import pandas as pd, numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
df = pd.read_csv("brasil_subitens_rotulados.csv")
X = (df.subitem + " | " + df.item).values; y = df.coicop.values; g = df.item_cod.values
pred = np.empty(len(df), dtype=object)
for tr, te in GroupKFold(5).split(X, y, g):
    m = make_pipeline(TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True),
                      LogisticRegression(C=20, max_iter=2000))
    m.fit(X[tr], y[tr]); pred[te] = m.predict(X[te])
acc = (pred == y).mean()
grp = np.array([c[:2] for c in y]); acc2 = (np.array([p[:2] for p in pred]) == grp).mean()
print(f"acurácia classe COICOP (nível 3, CV por item): {acc:.2%}")
print(f"acurácia divisão COICOP (2 dígitos):          {acc2:.2%}")
