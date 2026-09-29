"""Compatibiliza itens de uma cesta nacional com a COICOP usando um LLM (Claude) + few-shot da planilha do Brasil.
NÃO TESTADO contra a API (sem chave no ambiente de desenvolvimento).
Uso:
  export ANTHROPIC_API_KEY=...
  python llm_match.py eval  [N]                 # mede acurácia no Brasil (exemplos do próprio Brasil, excluindo o item testado)
  python llm_match.py evalchile [N]             # exemplos do Brasil -> testa no Chile (gabarito: chile_produtos_rotulados.csv)
  python llm_match.py run cesta_chile.csv       # CSV com colunas: codigo,item,subitem  -> chile_compat.csv
"""
import sys, json, random, pandas as pd, anthropic
MODEL = "claude-sonnet-5-5"
client = anthropic.Anthropic()
coicop = pd.read_csv("coicop.csv"); leaves = coicop[coicop.nivel >= 3]
cat = "\n".join(f"{r.coicop} {r.coicop_desc}" for r in leaves.itertuples())
gold = pd.read_csv("brasil_subitens_rotulados.csv")

def shots(exclude_item=None, k=60, seed=0):
    d = gold if exclude_item is None else gold[gold.item_cod != exclude_item]
    d = d.sample(min(k, len(d)), random_state=seed)
    return "\n".join(f"{r.item} / {r.subitem} -> {r.coicop}" for r in d.itertuples())

def classify(batch, exclude_item=None):
    prompt = f"""Você compatibiliza cestas de preços ao consumidor com a COICOP (classes de 3 níveis).
Classes COICOP disponíveis:\n{cat}\n
Exemplos validados (cesta do Brasil -> COICOP):\n{shots(exclude_item)}\n
Classifique cada linha abaixo na classe COICOP mais específica. Se nenhuma servir, use "NENHUMA".
Responda SOMENTE JSON: lista de objetos {{"i": <índice>, "coicop": "<código>", "confianca": <0-1>, "motivo": "<curto>"}}.
Linhas:\n""" + "\n".join(f"{i}. {r.item} / {r.subitem}" for i, r in enumerate(batch.itertuples()))
    out = client.messages.create(model=MODEL, max_tokens=4000, messages=[{"role": "user", "content": prompt}])
    txt = out.content[0].text; return json.loads(txt[txt.index("["): txt.rindex("]") + 1])

if sys.argv[1] == "eval":
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    test = gold.sample(n, random_state=1); ok = 0
    for r in test.itertuples():   # 1 por chamada para excluir o item testado dos exemplos
        p = classify(test.loc[[r.Index]], exclude_item=r.item_cod)[0]; ok += p["coicop"] == r.coicop
    print(f"acurácia nível 3: {ok/n:.2%} (n={n})")
elif sys.argv[1] == "evalchile":
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    cl = pd.read_csv("chile_produtos_rotulados.csv"); cl = cl[cl.nivel_gabarito == 3]   # só gabarito no nível de classe
    test = cl.sample(n, random_state=1).reset_index(drop=True); ok = ok_div = 0
    for i in range(0, n, 20):
        b = test.iloc[i:i + 20]
        for p in classify(b):
            g = test.coicop[i + p["i"]]; ok += p["coicop"] == g; ok_div += p["coicop"][:2] == g[:2]
    print(f"Brasil->Chile | classe: {ok/n:.2%} | divisão: {ok_div/n:.2%} (n={n})")
else:
    df = pd.read_csv(sys.argv[2]); res = []
    for s in range(0, len(df), 25):
        b = df.iloc[s:s + 25]; res += [{**p, "i": s + p["i"]} for p in classify(b)]
    r = pd.DataFrame(res).set_index("i"); out = df.join(r)
    out["revisar"] = (out.confianca < 0.7) | (out.coicop == "NENHUMA")
    out.to_csv(sys.argv[2].replace(".csv", "_compat.csv"), index=False)
    print(out.revisar.mean(), "das linhas marcadas p/ revisão humana")
