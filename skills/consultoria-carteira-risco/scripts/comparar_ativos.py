#!/usr/bin/env python3
"""Compara dois ativos: qual aumenta mais o risco (volatilidade e drawdown) de uma carteira?

Uso:
  python3 comparar_ativos.py --a NOMEA:fechamentos_a.csv --b NOMEB:fechamentos_b.csv [--cdi-aa 0.1365] [--peso 0.30] [--dd-max 0.08]
Cada CSV tem as colunas `data` (AAAA-MM-DD) e `fechamento` (de preferência ajustado por proventos).
Carteira de teste: (1 - peso) em CDI constante + peso no ativo. --dd-max é o limite de drawdown DO CLIENTE e deve vir dele (sem padrão).
Janelas curtas (< ~36 meses) ou dominadas por um dia dão leitura preliminar: o script avisa.
"""
import argparse
import csv
import math


def ler(arg):
    nome, caminho = arg.split(":", 1)
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        return nome, {r["data"]: float(str(r["fechamento"]).replace(",", ".")) for r in csv.DictReader(f)}


def ret(p): return [p[i] / p[i - 1] - 1 for i in range(1, len(p))]
def mean(x): return sum(x) / len(x)
def std(x): m = mean(x); return math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1))
def corr(a, b):
    ma, mb = mean(a), mean(b)
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
def beta(a, b):
    ma, mb = mean(a), mean(b)
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / sum((y - mb) ** 2 for y in b)
def vol(r): return std(r) * math.sqrt(252)
def maxdd(r):
    v = pk = 1.0; dd = 0.0
    for x in r:
        v *= 1 + x; pk = max(pk, v); dd = max(dd, (pk - v) / pk)
    return dd


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--a", required=True); ap.add_argument("--b", required=True)
    ap.add_argument("--cdi-aa", type=float, required=True, help="CDI anual (ex.: 0.1365), buscar a taxa do dia")
    ap.add_argument("--peso", type=float, default=0.30, help="peso do ativo na carteira de teste")
    ap.add_argument("--dd-max", type=float, default=None, help="limite de drawdown do cliente")
    a = ap.parse_args()
    (na, pa), (nb, pb) = ler(a.a), ler(a.b)
    datas = sorted(set(pa) & set(pb))
    ra, rb = ret([pa[d] for d in datas]), ret([pb[d] for d in datas])
    cdi = (1 + a.cdi_aa) ** (1 / 252) - 1
    print(f"{len(ra)} retornos diários ({datas[0]} a {datas[-1]})" + ("  [AVISO: janela curta, leitura preliminar]" if len(ra) < 750 else ""))
    for n, r in ((na, ra), (nb, rb)):
        print(f"{n}: vol anual {vol(r):.1%} | drawdown máx {maxdd(r):.1%} | pior dia {min(r):.1%}")
    print(f"correlação {na}×{nb}: {corr(ra, rb):.2f} | beta {na} vs {nb}: {beta(ra, rb):.2f}")
    print(f"\nCarteira ({1 - a.peso:.0%} CDI + {a.peso:.0%} no ativo):")
    for n, r in ((na, ra), (nb, rb)):
        c = [(1 - a.peso) * cdi + a.peso * x for x in r]
        print(f"  {n}: vol {vol(c):.1%} | drawdown máx {maxdd(c):.1%} | pior dia {min(c):.1%}")
        if a.dd_max:
            lo, hi = 0.0, 1.0
            for _ in range(40):
                m = (lo + hi) / 2
                cc = [(1 - m) * cdi + m * x for x in r]
                lo, hi = (m, hi) if maxdd(cc) <= a.dd_max else (lo, m)
            print(f"    peso máximo dentro do drawdown de {a.dd_max:.0%} (nesta janela): {lo:.0%}")
