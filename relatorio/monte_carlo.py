#!/usr/bin/env python3
"""Motor de simulação de Monte Carlo (cliente de 35 anos do texto de modelagem de risco).

Premissas = as do texto (retornos REAIS). Retornos mensais log-normais correlacionados via
decomposição de Cholesky; aportes mensais; rebalanceamento anual para a alocação-alvo.
Tudo em R$ de hoje (reais), portanto a inflação já está embutida nos retornos reais.
"""
import numpy as np

ATIVOS = ["Ações globais", "Títulos públicos indexados", "Títulos privados"]
MU = np.array([0.09, 0.04, 0.05])       # retorno médio real a.a. (aritmético)
SIG = np.array([0.16, 0.06, 0.10])      # volatilidade a.a.
CORR = np.array([[1.0, 0.2, 0.3],
                 [0.2, 1.0, 0.6],
                 [0.3, 0.6, 1.0]])
W_ALVO = np.array([0.60, 0.30, 0.10])
V0 = 200_000.0
APORTE = 1_000.0
META = 5_000_000.0
ANOS = 30
H = ANOS * 12
N = 10_000
SEED = 2026


def cov(sig=SIG, corr=CORR):
    return np.outer(sig, sig) * corr


def port_stats(w, mu=MU, sig=SIG, corr=CORR):
    w = np.asarray(w)
    return float(w @ mu), float(np.sqrt(w @ cov(sig, corr) @ w))


def normais(n=N, h=H, seed=SEED):
    return np.random.default_rng(seed).standard_normal((n, h, 3))


def t_student(n=N, h=H, df=5, seed=SEED + 1):
    """Caudas pesadas: t de Student padronizada (variância 1), um fator de escala por
    trajetória-mês (comum aos ativos, para que os extremos ocorram juntos)."""
    rng = np.random.default_rng(seed)
    z = rng.standard_normal((n, h, 3))
    chi = rng.chisquare(df, (n, h, 1))
    return z * np.sqrt((df - 2) / chi)


def sim(w, pmt=APORTE, Z=None, mu=MU, sig=SIG, corr=CORR, rebal="anual", banda=0.05,
        choque=None, horizonte=H, v0=V0):
    """Devolve (T, I, n_rebal): patrimônio mensal (n,h+1), índice de retorno (n,h+1) e nº médio de rebalanceamentos."""
    w = np.asarray(w, dtype=float)
    n = Z.shape[0]
    s_ln = np.sqrt(np.log(1 + (sig / (1 + mu)) ** 2))
    m_ln = np.log(1 + mu) - s_ln ** 2 / 2
    mm, ss = m_ln / 12, s_ln / np.sqrt(12)
    L = np.linalg.cholesky(corr)
    A = np.tile(v0 * w, (n, 1))
    T = np.empty((n, horizonte + 1)); T[:, 0] = v0
    I = np.empty((n, horizonte + 1)); I[:, 0] = 1.0
    eventos = np.zeros(n)
    for t in range(horizonte):
        A = A + pmt * w                                   # aporte novo compra pela alocação-alvo
        antes = A.sum(axis=1)
        r = mm + (Z[:, t, :] @ L.T) * ss                  # retornos log correlacionados
        if choque is not None and t // 12 in choque:      # choque determinístico em ações
            r[:, 0] = np.log(1 + choque[t // 12]) / 12
        A = A * np.exp(r)
        depois = A.sum(axis=1)
        if rebal == "anual" and (t + 1) % 12 == 0:
            A = depois[:, None] * w; eventos += 1
        elif rebal == "banda":
            desvio = np.abs(A / depois[:, None] - w).max(axis=1) > banda
            A[desvio] = depois[desvio, None] * w; eventos += desvio
        T[:, t + 1] = A.sum(axis=1)
        I[:, t + 1] = I[:, t] * depois / antes
    return T, I, float(eventos.mean())


def maxdd(I):
    pico = np.maximum.accumulate(I, axis=1)
    return (1 - I / pico).max(axis=1)


def resumo(T, I, meta=META):
    f = T[:, -1]
    dd = maxdd(I)
    return {
        "p_meta": float((f >= meta).mean()),
        "media": float(f.mean()), "mediana": float(np.median(f)),
        "pct": {q: float(np.percentile(f, q)) for q in (5, 10, 25, 50, 75, 90, 95)},
        "p_dd20": float((dd > 0.20).mean()), "p_dd30": float((dd > 0.30).mean()), "p_dd40": float((dd > 0.40).mean()),
        "dd_med": float(np.median(dd)),
    }


def aporte_para_prob(prob, w, Z, **kw):
    lo, hi = 0.0, 20_000.0
    for _ in range(30):
        mid = (lo + hi) / 2
        T, _, _ = sim(w, pmt=mid, Z=Z, **kw)
        lo, hi = (mid, hi) if (T[:, -1] >= META).mean() < prob else (lo, mid)
    return (lo + hi) / 2


def det(w, pmt=APORTE, mu=MU, horizonte=H, v0=V0):
    """Trajetória determinística com o retorno esperado constante (o 'cenário linear' do texto)."""
    r = float(np.asarray(w) @ mu)
    i = (1 + r) ** (1 / 12) - 1
    v, out = v0, [v0]
    for _ in range(horizonte):
        v = (v + pmt) * (1 + i)
        out.append(v)
    return np.array(out)


if __name__ == "__main__":
    Z = normais()
    T, I, ev = sim(W_ALVO, Z=Z)
    r = resumo(T, I)
    print("retorno/vol carteira:", port_stats(W_ALVO))
    print("P(meta):", r["p_meta"], "| média", round(r["media"]), "mediana", round(r["mediana"]))
    print("percentis:", {k: round(v) for k, v in r["pct"].items()})
    print("P(DD>20/30/40):", r["p_dd20"], r["p_dd30"], r["p_dd40"], "| dd mediano", r["dd_med"])
    print("determinístico final:", round(det(W_ALVO)[-1]))
    print("aporte p/ 70%:", round(aporte_para_prob(0.70, W_ALVO, Z)))
