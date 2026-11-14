#!/usr/bin/env python3
"""Lê a planilha de ativos (formato assets/modelo_ativos.csv) e, se houver, o histórico mensal
(assets/modelo_historico_mensal.csv), e devolve os parâmetros para o motor monte_carlo.py:
nomes, mu (retorno real a.a.), sig (volatilidade a.a.) e a matriz de correlação (PSD).

Uso:  python3 carregar_ativos.py ativos.csv [historico.csv]
Como biblioteca:  from carregar_ativos import carregar
"""
import csv
import sys

import numpy as np

CORR_OUTRA_CLASSE = 0.30   # premissa quando não há histórico
CORR_MESMA_CLASSE = 0.70


def _num(v):
    v = (v or "").strip().replace("%", "")
    if v == "":
        return None
    return float(v.replace(".", "").replace(",", ".")) if "," in v else float(v)


def _psd(c):
    """Garante matriz de correlação positiva semidefinida (corta autovalores negativos)."""
    vals, vecs = np.linalg.eigh(c)
    vals = np.clip(vals, 1e-8, None)
    c = vecs @ np.diag(vals) @ vecs.T
    d = np.sqrt(np.diag(c))
    c = c / np.outer(d, d)
    np.fill_diagonal(c, 1.0)
    return c


def carregar(path_ativos, path_hist=None):
    avisos, ativos = [], []
    with open(path_ativos, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row["nome"].strip():
                ativos.append(row)
    nomes = [a["nome"].strip() for a in ativos]
    classes = [a.get("classe", "").strip() for a in ativos]
    mu = [_num(a.get("retorno_esperado_real_aa")) for a in ativos]
    sig = [_num(a.get("volatilidade_aa")) for a in ativos]

    hist = None
    if path_hist:
        with open(path_hist, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        cols = [c for c in rows[0].keys() if c != "data"]
        if all(n in cols for n in nomes):
            hist = np.array([[_num(r[n]) for n in nomes] for r in rows], dtype=float)
        else:
            faltam = [n for n in nomes if n not in cols]
            avisos.append(f"histórico ignorado: faltam colunas para {faltam}")

    if hist is not None:
        meses = hist.shape[0]
        if meses < 24:
            avisos.append(f"histórico curto ({meses} meses): volatilidade e correlação pouco confiáveis")
        vol_h = hist.std(axis=0, ddof=1) * np.sqrt(12)
        for i, v in enumerate(sig):
            if v is None:
                sig[i] = float(vol_h[i]); avisos.append(f"volatilidade de '{nomes[i]}' estimada do histórico")
        corr = np.corrcoef(hist.T) if meses >= 12 else None
        if corr is None:
            avisos.append("histórico < 12 meses: correlação por premissa")
    else:
        corr = None

    if corr is None:
        n = len(nomes)
        corr = np.full((n, n), CORR_OUTRA_CLASSE)
        for i in range(n):
            for j in range(n):
                if classes[i] and classes[i] == classes[j]:
                    corr[i, j] = CORR_MESMA_CLASSE
        np.fill_diagonal(corr, 1.0)
        avisos.append(f"correlação por premissa ({CORR_MESMA_CLASSE:.1f} mesma classe, {CORR_OUTRA_CLASSE:.1f} entre classes)")

    faltando = [nomes[i] for i in range(len(nomes)) if mu[i] is None or sig[i] is None]
    if faltando:
        raise ValueError(f"sem retorno esperado ou volatilidade (e sem histórico para estimar): {faltando}")
    avisos.append("linhas com 'EXEMPLO' no nome são fictícias" if any("EXEMPLO" in n for n in nomes) else "")
    return {"nomes": nomes, "classes": classes, "mu": np.array(mu), "sig": np.array(sig),
            "corr": _psd(np.array(corr)), "avisos": [a for a in avisos if a], "ativos": ativos}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    r = carregar(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(f"{'ativo':34s} {'classe':14s} {'ret.real':>9s} {'vol':>7s}")
    for n, c, m, s in zip(r["nomes"], r["classes"], r["mu"], r["sig"]):
        print(f"{n:34s} {c:14s} {m:9.1%} {s:7.1%}")
    print("\ncorrelação:\n", np.round(r["corr"], 2))
    for a in r["avisos"]:
        print("AVISO:", a)
