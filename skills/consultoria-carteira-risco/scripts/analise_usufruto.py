#!/usr/bin/env python3
"""Sustentabilidade de um plano de usufruto (retiradas mensais reais constantes) sem aportes.

Uso:  python3 analise_usufruto.py --patrimonio 2000000 --retirada 12000 --idade 55 [--ate 80 90] [--retornos 3 4 5 6 7]
Tudo em R$ reais (poder de compra de hoje); retornos são REAIS (acima do IPCA), brutos de imposto e taxas.
Convenção do plano (PDFs da Portfel): V[t+1] = V[t]*(1+r) - 12*retirada, em base anual. A simulação usa passo mensal,
retirada no início do mês e retornos log-normais independentes (sem reversão à média).
"""
import argparse
import math

import numpy as np


def plano_anual(pv, saque_mes, r, anos):
    v, out = pv, [pv]
    for _ in range(anos):
        v = v * (1 + r) - 12 * saque_mes
        out.append(v)
    return out


def anos_ate_zerar(pv, saque_mes, r):
    S = 12 * saque_mes
    if r == 0:
        return pv / S
    if pv * r >= S:
        return math.inf
    return math.log(S / (S - pv * r)) / math.log(1 + r)


def capital_necessario(saque_mes, r, anos):
    S = 12 * saque_mes
    return S * anos if r == 0 else S * (1 - (1 + r) ** -anos) / r


def retirada_sustentavel(pv, r, anos):
    """Retirada mensal que zera o patrimônio exatamente ao fim do horizonte (cenário determinístico)."""
    return pv / (12 * capital_necessario(1 / 12, r, anos)) if r else pv / (12 * anos)


def mc_sucesso(pv, saque_mes, mu, sigma, anos, n=10_000, seed=2026, z=None):
    """Probabilidade de o patrimônio durar `anos` e percentis do que sobra."""
    meses = anos * 12
    z = np.random.default_rng(seed).standard_normal((n, meses)) if z is None else z[:, :meses]
    s_ln = math.sqrt(math.log(1 + (sigma / (1 + mu)) ** 2))
    m_ln = math.log(1 + mu) - s_ln ** 2 / 2
    r = np.exp(m_ln / 12 + z * s_ln / math.sqrt(12))          # fator mensal
    v = np.full(n, float(pv))
    vivo = np.ones(n, bool)
    for t in range(meses):
        v = np.where(vivo, (v - saque_mes) * r[:, t], 0.0)
        vivo &= v > 0
    return float(vivo.mean()), {q: float(np.percentile(v, q)) for q in (10, 50, 90)}


def retirada_para_prob(pv, mu, sigma, anos, prob, n=6000, seed=2026):
    z = np.random.default_rng(seed).standard_normal((n, anos * 12))
    lo, hi = 0.0, pv / 12
    for _ in range(28):
        mid = (lo + hi) / 2
        p, _ = mc_sucesso(pv, mid, mu, sigma, anos, n, seed, z)
        lo, hi = (mid, hi) if p >= prob else (lo, mid)
    return lo


def brl(x): return "R$ " + f"{x:,.0f}".replace(",", ".")
def pc(x, d=1): return f"{x * 100:.{d}f}%".replace(".", ",")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--patrimonio", type=float, required=True)
    ap.add_argument("--retirada", type=float, required=True, help="retirada mensal em R$ reais")
    ap.add_argument("--idade", type=int, required=True)
    ap.add_argument("--ate", type=int, nargs="+", default=[80, 90])
    ap.add_argument("--retornos", type=float, nargs="+", default=[3, 4, 5, 6, 7], help="retornos reais a.a. em %%")
    a = ap.parse_args()
    pv, w = a.patrimonio, a.retirada
    print(f"Patrimônio {brl(pv)} | retirada {brl(w)}/mês ({pc(12 * w / pv)} ao ano do patrimônio) | idade {a.idade}\n")
    print("Quando o patrimônio acaba (cenário constante, sem risco):")
    for r in a.retornos:
        n = anos_ate_zerar(pv, w, r / 100)
        print(f"  IPCA+{r:g}%: " + ("nunca (retirada < rendimento)" if math.isinf(n) else f"{n:.1f} anos, aos {a.idade + n:.0f} anos"))
    print("\nRetirada mensal sustentável (zera o patrimônio no horizonte):")
    print("  retorno real | " + " | ".join(f"até {i} anos" for i in a.ate))
    for r in a.retornos:
        print(f"  IPCA+{r:g}%".ljust(15) + "| " + " | ".join(brl(retirada_sustentavel(pv, r / 100, i - a.idade)).rjust(10) for i in a.ate))
    print("\nCapital necessário para a retirada pedida:")
    for r in a.retornos:
        print(f"  IPCA+{r:g}%: " + " | ".join(f"até {i}: {brl(capital_necessario(w, r / 100, i - a.idade))}" for i in a.ate))
