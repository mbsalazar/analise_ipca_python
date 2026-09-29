import argparse
from . import armazem as A, pipeline as P
def main(argv=None):
    ap = argparse.ArgumentParser(prog="harmonizacao", description="IPC harmonizado na COICOP")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("atualizar", help="coleta + publica"); a.add_argument("--fontes", default=",".join(P.FONTES)); a.add_argument("--desde", help="YYYY-MM (padrão: histórico completo)")
    sub.add_parser("publicar", help="só recalcula o publicado a partir do curado")
    sub.add_parser("status", help="resumo do que existe")
    x = ap.parse_args(argv)
    if x.cmd == "atualizar": P.coletar(x.fontes.split(","), x.desde); P.publicar()
    elif x.cmd == "publicar": P.publicar()
    else:
        d = A.ler("ipc_harmonizado", "publicado")
        print(d.groupby(["pais"]).agg(series=("coicop", "nunique"), ate=("data", "max")).to_string() if len(d) else "vazio")
if __name__ == "__main__": main()
