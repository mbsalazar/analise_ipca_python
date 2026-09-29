# harmonizacao — IPC harmonizado na COICOP

Todo mês: **coletar o divulgado → passar pelo de-para → publicar o IPC harmonizado.**

```
pip install -e .[dev]
harmonizacao atualizar --desde 2026-06     # coleta incremental + republica (sem --desde: histórico completo)
harmonizacao atualizar --fontes ibge       # só o Brasil
harmonizacao publicar                      # recalcula o publicado a partir do curado
harmonizacao status
pytest
```

## Camadas (parquet em `dados/`)
| Camada | Tabela | Chave | Conteúdo |
|---|---|---|---|
| curado | `item_nacional` | pais, sistema_local, cod_local | cesta como o país publica (hierarquia) |
| curado | `serie_nacional` | + data, fonte | índice e/ou variação mensal, com a base declarada |
| curado | `peso_nacional` | + data, fonte | pesos e escala (`pct`, `permil`) |
| publicado | `ipc_harmonizado` | pais, sistema, coicop, data | **produto final**: índice (2020=100), var. mensal e 12m, peso, cobertura, origem |

`dados/curado` é regenerável (não versionado); `dados/publicado` é o resultado. Gravação por **upsert por chave**: uma revisão da fonte substitui só as linhas afetadas.

## De-para (`mapeamentos/<PAIS>.csv`)
Colunas: `pais, sistema_local, cod_local, sistema_coicop, coicop, tipo, parcela, metodo, confianca, revisado`.
- Mapear sempre no **nível mais baixo publicado** (Brasil: subitem, 7 dígitos), nunca dois níveis da mesma cesta (dupla contagem).
- Item que se divide em duas classes: duas linhas com `parcela` somando 1.
- Países cuja fonte já é COICOP (Eurostat, BLS, OCDE) não precisam de de-para: passam direto.
- País novo: classificar a cesta (`../coicop_ml/llm_match.py`), revisar `confianca < 0.7`, salvar o CSV e registrar um conector.

## Método (validado)
- Agregação: `var(nó, t) = Σ w_i(t)·v_i(t) / Σ w_i(t)` sobre os componentes mapeados; **peso do mês t com a variação do mês t**. Teste contra o IBGE: reproduzir grupos/itens do IPCA a partir dos subitens dá erro máx. 0,008 p.p. (peso do mês t-1 daria até 0,4 p.p.).
- Índice: encadeado das variações; **base comum 2020 = 100** (média; exige 12 meses de 2020, senão fica vazio em vez de inventar base).
- Total do Brasil (`coicop=00`): acumulado em 12 meses fica a ≤0,013 p.p. do oficial (arredondamento das variações publicadas).
- Nós COICOP: a classe mapeada e todos os ancestrais (`01.1.1` → `01.1` → `01` → `00`).
- Várias fontes para a mesma série: fica a de dado mais recente; empate → mais longa → prioridade fixa (`agregar.PRIORIDADE`). A coluna `fonte` permite filtrar.

## Limites conhecidos
- Sistemas COICOP 1999 e 2018 convivem (`sistema`); a ponte oficial está em `../coicop_ml/dados/coicop_correspondencia_2018_1999.csv` e **ainda não é aplicada** no pipeline.
- Pesos publicados só do Eurostat (‰/ano) e do IBGE (mensal). BLS/OCDE sem pesos por ora.
- Chile e México: sem conector da fonte nacional; hoje só aparecem pelos agregados da OCDE.
- Brasil: IPCA por subitem só desde jan/2020 (SIDRA 7060); série anterior está em outra tabela.
