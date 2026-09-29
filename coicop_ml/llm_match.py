"""Compatibiliza a cesta de QUALQUER país diretamente com a COICOP, usando um LLM (Claude).
Os exemplos (few-shot) vêm de gabarito_paises.csv (colunas pais,codigo,item,subitem,coicop): cada país já compatibilizado
com a COICOP. Para incluir um país novo depois de revisado, basta acrescentar as linhas a esse arquivo.
NÃO TESTADO contra a API (sem chave no ambiente de desenvolvimento).
Uso:
  export ANTHROPIC_API_KEY=...
  python llm_match.py eval Chile [N]        # mede acurácia em um país com gabarito, usando exemplos SÓ dos outros países
  python llm_match.py run mexico.csv Mexico # CSV com colunas: codigo,item,subitem -> mexico_compat.csv
"""
import sys, json, random, pandas as pd, anthropic
MODEL = "claude-sonnet-5-5"
client = anthropic.Anthropic()
coicop = pd.read_csv("coicop.csv"); leaves = coicop[coicop.nivel >= 3]
cat = "\n".join(f"{r.coicop} {r.coicop_desc}" for r in leaves.itertuples())
gold = pd.read_csv("gabarito_paises.csv", dtype=str)

def shots(exclude_pais=None, k=60, seed=0):
    d = gold if exclude_pais is None else gold[gold.pais != exclude_pais]
    d = d.sample(min(k, len(d)), random_state=seed)
    return "\n".join(f"[{r.pais}] {r.item} / {r.subitem} -> {r.coicop}" for r in d.itertuples())

def classify(batch, exclude_pais=None):
    prompt = f"""Você compatibiliza cestas de preços ao consumidor com a COICOP (classes de 3 níveis).
Classes COICOP disponíveis:\n{cat}\n
Exemplos validados (cesta nacional -> COICOP):\n{shots(exclude_pais)}\n
Classifique cada linha abaixo na classe COICOP mais específica. Se nenhuma servir, use "NENHUMA".
Responda SOMENTE JSON: lista de objetos {{"i": <índice>, "coicop": "<código>", "confianca": <0-1>, "motivo": "<curto>"}}.
Linhas:\n""" + "\n".join(f"{i}. {r.item} / {r.subitem}" for i, r in enumerate(batch.itertuples()))
    out = client.messages.create(model=MODEL, max_tokens=4000, messages=[{"role": "user", "content": prompt}])
    txt = out.content[0].text; return json.loads(txt[txt.index("["): txt.rindex("]") + 1])

if sys.argv[1] == "eval":
    pais = sys.argv[2]; n = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    test = gold[gold.pais == pais].sample(n, random_state=1).reset_index(drop=True); ok = ok_div = 0
    for i in range(0, n, 20):
        for p in classify(test.iloc[i:i + 20], exclude_pais=pais):
            g = test.coicop[i + p["i"]]; ok += p["coicop"] == g; ok_div += p["coicop"][:2] == g[:2]
    print(f"{pais} | classe: {ok/n:.2%} | divisão: {ok_div/n:.2%} (n={n})")
else:
    df = pd.read_csv(sys.argv[2]); res = []
    for s0 in range(0, len(df), 25):
        b = df.iloc[s0:s0 + 25]; res += [{**p, "i": s0 + p["i"]} for p in classify(b, exclude_pais=sys.argv[3] if len(sys.argv) > 3 else None)]
    out = df.join(pd.DataFrame(res).set_index("i"))
    out["revisar"] = (out.confianca < 0.7) | (out.coicop == "NENHUMA")
    out.to_csv(sys.argv[2].replace(".csv", "_compat.csv"), index=False)
    print(out.revisar.mean(), "das linhas marcadas p/ revisão humana")
