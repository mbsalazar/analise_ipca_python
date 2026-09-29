import re
def pontuar(cod: str):
    """'CP0111' -> '01.1.1'; 'CP00' -> '00'; None se não for código COICOP puro (ex.: 'FOOD', 'TOT_X_NRG')."""
    m = re.fullmatch(r"(?:CP|)(\d{2})(\d*)", str(cod))
    return None if not m else ".".join([m.group(1)] + list(m.group(2)))
def ancestrais(cod: str):
    """'01.1.2' -> ['01.1', '01', '00']"""
    p = cod.split("."); return [".".join(p[:i]) for i in range(len(p) - 1, 0, -1)] + ["00"]
def nivel(cod: str): return 0 if cod == "00" else cod.count(".") + 1
