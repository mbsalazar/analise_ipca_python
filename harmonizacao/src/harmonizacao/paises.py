"""Códigos de país: tudo em ISO-3. O Eurostat usa ISO-2 com exceções (EL, UK, XK); agregados ficam de fora."""
import pycountry
EXCECOES = {"EL": "GRC", "UK": "GBR", "XK": "XKX"}
AGREGADOS = {"EA", "EA19", "EA20", "EU", "EU27_2020", "EU28", "EEA", "OECD", "OECDE", "G7", "G20"}
def iso3(cod: str):
    if cod in AGREGADOS: return None
    if cod in EXCECOES: return EXCECOES[cod]
    if len(cod) == 2:
        p = pycountry.countries.get(alpha_2=cod); return p.alpha_3 if p else None
    return cod
