# Harmonização de IPC na COICOP
Fluxo: `conectores/*.py` (baixam BLS/Eurostat/OCDE) -> `unificar.py` -> `dados/indices_unificado.csv.gz`
(colunas: fonte, pais [ISO-3], sistema [COICOP1999|COICOP2018], coicop [01.1.1], data, indice; bases de índice diferem por fonte).
`dados/coicop_correspondencia_2018_1999.csv`: tabela oficial da ONU. `build_*.py`, `llm_match.py`, `gabarito_paises.csv`: classificação de cestas nacionais (Brasil, Chile) na COICOP.
Limites: índices de fontes diferentes têm bases diferentes (não comparar níveis sem rebasear); classes COICOP só onde a fonte publica.
