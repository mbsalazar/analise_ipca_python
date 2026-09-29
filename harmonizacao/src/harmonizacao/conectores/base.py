"""Contrato de um conector: devolve tabelas normalizadas (esquema.TABELAS). Nada de regra de negócio aqui."""
from dataclasses import dataclass, field
import pandas as pd
@dataclass
class Resultado:
    itens: pd.DataFrame = field(default_factory=pd.DataFrame)     # item_nacional
    series: pd.DataFrame = field(default_factory=pd.DataFrame)    # serie_nacional
    pesos: pd.DataFrame = field(default_factory=pd.DataFrame)     # peso_nacional
class Conector:
    pais: str = ""              # ISO-3 (ou lista em conectores multipaís)
    nativo_coicop: bool = False  # True: os códigos já são COICOP (sem de-para)
    def coletar(self, desde: str | None = None) -> Resultado:   # desde = 'YYYY-MM'
        raise NotImplementedError
