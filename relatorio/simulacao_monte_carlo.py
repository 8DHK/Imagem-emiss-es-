#!/usr/bin/env python3
"""Gera relatorio/simulacao_monte_carlo.html: Monte Carlo + rebalanceamento (premissas do texto)."""
import json
from pathlib import Path

import numpy as np

import monte_carlo as mc

W = mc.W_ALVO
Z = mc.normais()
Zt = mc.t_student()


def pct(x, d=1): return f"{x * 100:.{d}f}".replace(".", ",") + "%"
def brl(x): return "R$ " + f"{x:,.0f}".replace(",", ".")
def mi(x, d=2): return "R$ " + f"{x / 1e6:.{d}f}".replace(".", ",") + " mi"
def num(x, d=2): return f"{x:.{d}f}".replace(".", ",")


# ---------------------------------------------------------------- 1. Base
T, I, _ = mc.sim(W, Z=Z)
base = mc.resumo(T, I)
ret_p, vol_p = mc.port_stats(W)
det_path = mc.det(W)
anos = np.arange(0, mc.ANOS + 1)
fan = {q: np.percentile(T[:, ::12], q, axis=0) for q in (5, 25, 50, 75, 95)}
final = T[:, -1]

# ---------------------------------------------------------------- 2. Alocações
ALOCS = [("Conservadora", [0.20, 0.60, 0.20]), ("Moderada", [0.40, 0.40, 0.20]),
         ("Cliente (60/30/10)", [0.60, 0.30, 0.10]), ("Agressiva", [0.80, 0.10, 0.10]), ("100% ações", [1.0, 0.0, 0.0])]
aloc_rows = []
for nome, w in ALOCS:
    Ta, Ia, _ = mc.sim(w, Z=Z)
    r = mc.resumo(Ta, Ia)
    er, vv = mc.port_stats(w)
    aloc_rows.append({"nome": nome, "w": w, "er": er, "vol": vv, **r})

# ---------------------------------------------------------------- 3. Estresse (sequência de retornos)
SEQ = {0: -0.30, 1: -0.10, 2: 0.0}
cedo = mc.sim(W, Z=Z, choque=SEQ)
tarde = mc.sim(W, Z=Z, choque={27: -0.30, 28: -0.10, 29: 0.0})
est_cedo, est_tarde = mc.resumo(cedo[0], cedo[1]), mc.resumo(tarde[0], tarde[1])

# ---------------------------------------------------------------- 4. Alavancas
meta_70 = float(np.percentile(final, 30))                 # meta atingida em 70% das trajetórias
aporte_70 = mc.aporte_para_prob(0.70, W, Z)
W_AGR = [0.80, 0.10, 0.10]
aporte_70_agr = mc.aporte_para_prob(0.70, W_AGR, Z)

# ---------------------------------------------------------------- 5. Sensibilidade às premissas
def variante(nome, **kw):
    Tv, Iv, _ = mc.sim(W, **kw)
    return {"nome": nome, **mc.resumo(Tv, Iv)}

corr_estresse = np.full((3, 3), 0.8); np.fill_diagonal(corr_estresse, 1.0)
sens = [
    {"nome": "Base (premissas do texto)", **base},
    variante("Retornos 1 p.p. menores (todas as classes)", Z=Z, mu=mc.MU - 0.01),
    variante("Volatilidades 20% maiores", Z=Z, sig=mc.SIG * 1.2),
    variante("Caudas pesadas (t de Student, 5 g.l.)", Z=Zt),
    variante("Correlações de crise (0,8 entre todas)", Z=Z, corr=corr_estresse),
]

# ---------------------------------------------------------------- 6. Rebalanceamento
reb = []
for nome, kw in [("Sem rebalancear", {"rebal": "nenhum"}), ("Anual", {"rebal": "anual"}),
                 ("Por banda de 5 p.p.", {"rebal": "banda", "banda": 0.05})]:
    Tr, Ir, ev = mc.sim(W, Z=Z, **kw)
    reb.append({"nome": nome, "ev": ev, **mc.resumo(Tr, Ir)})

# ---------------------------------------------------------------- 7. Alocação tática (sobreposição +5 p.p. ações)
W_TAT = [0.65, 0.25, 0.10]
Tt, It, _ = mc.sim(W_TAT, Z=Z)
tat = mc.resumo(Tt, It)
er_t, vol_t = mc.port_stats(W_TAT)

# ---------------------------------------------------------------- 8. Rebalanceamento linear (exemplo do texto)
VT = 1_000_000
cls = [("Ações", 0.60, 0.65), ("Títulos públicos", 0.30, 0.28), ("Imóveis", 0.10, 0.07)]
reb_lin = [[n, pct(wa, 0), pct(wc, 0), brl(VT * wc), brl(VT * wa),
            ("vender " + brl(VT * (wc - wa))) if wc > wa else ("comprar " + brl(VT * (wa - wc))),
            f"{(wc - wa) * 100:+.0f} p.p.",
            "sim" if abs(wc - wa) >= 0.05 else "não"] for n, wa, wc in cls]

# ---------------------------------------------------------------- SVG helpers
CHARTS = {}


def fan_chart():
    w, h, ml, mr, mt, mb = 760, 340, 56, 128, 14, 34
    X = lambda i: ml + i * (w - ml - mr) / mc.ANOS
    ymax = 6.0
    Y = lambda v: h - mb - (v / 1e6) * (h - mb - mt) / ymax
    o = [f'<svg class="chart" id="g1" viewBox="0 0 {w} {h}" role="img" aria-labelledby="g1-t">']
    for t in range(0, 7):
        o.append(f'<line x1="{ml}" x2="{w - mr}" y1="{Y(t * 1e6):.1f}" y2="{Y(t * 1e6):.1f}" class="grid"/>')
        o.append(f'<text x="{ml - 8}" y="{Y(t * 1e6) + 4:.1f}" class="tick" text-anchor="end">{t}</text>')
    for i in range(0, 31, 5):
        o.append(f'<text x="{X(i):.1f}" y="{h - 12}" class="tick" text-anchor="middle">{35 + i}a</text>')
    o.append(f'<line x1="{ml}" x2="{w - mr}" y1="{Y(0)}" y2="{Y(0)}" class="axis"/>')

    def poly(lo, hi, cls_):
        pts = [f"{X(i):.1f},{Y(hi[i]):.1f}" for i in range(31)] + [f"{X(i):.1f},{Y(lo[i]):.1f}" for i in range(30, -1, -1)]
        o.append(f'<polygon points="{" ".join(pts)}" class="{cls_}"/>')
    poly(fan[5], fan[95], "band"); poly(fan[25], fan[75], "band2")
    path = lambda v: " ".join(f"{'M' if i == 0 else 'L'}{X(i):.1f},{Y(v[i]):.1f}" for i in range(31))
    o.append(f'<path d="{path(fan[50])}" fill="none" stroke="var(--s1)" stroke-width="2.5" stroke-linejoin="round"/>')
    o.append(f'<path d="{path(det_path[::12])}" fill="none" stroke="var(--ink2)" stroke-width="1.5" stroke-dasharray="5 4"/>')
    o.append(f'<line x1="{ml}" x2="{w - mr}" y1="{Y(5e6):.1f}" y2="{Y(5e6):.1f}" stroke="var(--s2)" stroke-width="2" stroke-dasharray="6 4"/>')
    o.append(f'<text x="{ml + 8}" y="{Y(5e6) - 6:.1f}" class="dlabel" style="fill:var(--ink)">Meta: R$ 5 mi</text>')
    rot = [(fan[95][-1], "P95"), (fan[50][-1], "Mediana"), (det_path[-1], "Retorno médio fixo"), (fan[5][-1], "P5")]
    ys = []
    for v, n in sorted(rot, key=lambda t: Y(t[0])):
        yy = Y(v)
        if ys and yy - ys[-1] < 15: yy = ys[-1] + 15
        ys.append(yy)
        o.append(f'<text x="{w - mr + 6}" y="{yy + 4:.1f}" class="dlabel">{n}</text>')
    o.append('<line class="xhair" y1="%d" y2="%d" x1="0" x2="0" visibility="hidden"/>' % (mt, h - mb))
    o.append(f'<rect class="hit" x="{ml}" y="{mt}" width="{w - ml - mr}" height="{h - mt - mb}" fill="transparent"/></svg>')
    CHARTS["g1"] = {"w": w, "xs": [round(X(i), 1) for i in range(31)], "xlabels": [f"{35 + i} anos (ano {i})" for i in range(31)],
                    "rows": [[f"P95: {mi(fan[95][i])}", f"P75: {mi(fan[75][i])}", f"Mediana: {mi(fan[50][i])}",
                              f"P25: {mi(fan[25][i])}", f"P5: {mi(fan[5][i])}", f"Retorno médio fixo: {mi(det_path[::12][i])}"]
                             for i in range(31)]}
    return "\n".join(o)


def hist_chart():
    edges = [0, 1e6, 2e6, 3e6, 4e6, 5e6, 6e6, 8e6, float("inf")]
    labs = ["< 1", "1–2", "2–3", "3–4", "4–5", "5–6", "6–8", "> 8"]
    cnt = [float(((final >= a) & (final < b)).mean()) for a, b in zip(edges[:-1], edges[1:])]
    w, h, ml, mr, mt, mb = 760, 260, 50, 16, 24, 40
    bw = (w - ml - mr) / len(cnt)
    ymax = 0.40
    Y = lambda v: h - mb - v / ymax * (h - mb - mt)
    o = [f'<svg class="chart" id="g2" viewBox="0 0 {w} {h}" role="img" aria-labelledby="g2-t">']
    for t in (0, .1, .2, .3, .4):
        o.append(f'<line x1="{ml}" x2="{w - mr}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" class="grid"/>')
        o.append(f'<text x="{ml - 8}" y="{Y(t) + 4:.1f}" class="tick" text-anchor="end">{int(t * 100)}%</text>')
    for i, (c, l) in enumerate(zip(cnt, labs)):
        x = ml + i * bw + 6
        cor = "var(--s1)" if i >= 5 else "var(--mut)"
        o.append(f'<rect x="{x:.1f}" y="{Y(c):.1f}" width="{bw - 12:.1f}" height="{max(Y(0) - Y(c), 1):.1f}" rx="3" fill="{cor}"><title>R$ {l} mi: {pct(c)} das trajetórias</title></rect>')
        o.append(f'<text x="{x + (bw - 12) / 2:.1f}" y="{Y(c) - 6:.1f}" class="dlabel" text-anchor="middle" style="fill:var(--ink)">{pct(c)}</text>')
        o.append(f'<text x="{x + (bw - 12) / 2:.1f}" y="{h - 20}" class="tick" text-anchor="middle">{l}</text>')
    o.append(f'<text x="{ml + (w - ml - mr) / 2:.1f}" y="{h - 4}" class="tick" text-anchor="middle">Patrimônio real aos 65 anos (R$ milhões)</text>')
    o.append(f'<line x1="{ml}" x2="{w - mr}" y1="{Y(0)}" y2="{Y(0)}" class="axis"/></svg>')
    return "\n".join(o), cnt


def bar_h(cid, items, xmax, fmt, ref=None, ref_lab=""):
    w, rowh, ml, mr, mt = 760, 40, 170, 70, 8
    h = mt + rowh * len(items) + 26
    X = lambda v: ml + v / xmax * (w - ml - mr)
    o = [f'<svg class="chart" id="{cid}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="{cid}-t">']
    for t in range(0, int(xmax * 100) + 1, 20):
        o.append(f'<line x1="{X(t / 100):.1f}" x2="{X(t / 100):.1f}" y1="{mt}" y2="{h - 22}" class="grid"/>')
        o.append(f'<text x="{X(t / 100):.1f}" y="{h - 6}" class="tick" text-anchor="middle">{t}%</text>')
    for i, (n, v, emph) in enumerate(items):
        y0 = mt + i * rowh + 6
        o.append(f'<text x="{ml - 10}" y="{y0 + 16}" class="dlabel" text-anchor="end" style="fill:var(--ink)">{n}</text>')
        o.append(f'<rect x="{ml}" y="{y0}" width="{max(X(v) - ml, 1.5):.1f}" height="22" rx="3" fill="{"var(--s1)" if emph else "var(--mut)"}"><title>{n}: {fmt(v)}</title></rect>')
        o.append(f'<text x="{X(v) + 8:.1f}" y="{y0 + 16}" class="dlabel" style="fill:var(--ink)">{fmt(v)}</text>')
    if ref is not None:
        o.append(f'<line x1="{X(ref):.1f}" x2="{X(ref):.1f}" y1="{mt}" y2="{h - 22}" stroke="var(--s2)" stroke-width="2" stroke-dasharray="6 4"/>')
        o.append(f'<text x="{X(ref) + 6:.1f}" y="{mt + 10}" class="dlabel" style="fill:var(--ink)">{ref_lab}</text>')
    o.append(f'<line x1="{ml}" x2="{ml}" y1="{mt}" y2="{h - 22}" class="axis"/></svg>')
    return "\n".join(o)


def tabela(cab, linhas, cls="num"):
    h = "".join(f"<th>{c}</th>" for c in cab)
    r = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in l) + "</tr>" for l in linhas)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{r}</tbody></table></div>'


g1 = fan_chart()
g2, cnt = hist_chart()
g3 = bar_h("g3", [(a["nome"], a["p_meta"], a["nome"].startswith("Cliente")) for a in aloc_rows], 0.4, lambda v: pct(v))
g4 = bar_h("g4", [(a["nome"], a["p_dd30"], a["nome"].startswith("Cliente")) for a in aloc_rows], 1.0, lambda v: pct(v))

# ---------------------------------------------------------------- Tabelas
tab_prem = tabela(["Classe", "Peso", "Retorno real a.a.", "Volatilidade a.a."],
                  [[n, pct(w, 0), pct(m, 0), pct(s, 0)] for n, w, m, s in zip(mc.ATIVOS, W, mc.MU, mc.SIG)]
                  + [["<strong>Carteira</strong>", "100%", f"<strong>{pct(ret_p)}</strong>", f"<strong>{pct(vol_p)}</strong>"]])
tab_corr = tabela(["Correlação", "Valor"], [["Ações × títulos públicos", "0,2"], ["Ações × títulos privados", "0,3"], ["Públicos × privados", "0,6"]])
tab_pct = tabela(["Percentil", "Patrimônio real aos 65", "Leitura"],
                 [["P5", mi(base["pct"][5]), "5% das trajetórias terminam abaixo disso"],
                  ["P10", mi(base["pct"][10]), "10% abaixo"], ["P25", mi(base["pct"][25]), ""],
                  ["P50 (mediana)", mi(base["pct"][50]), "metade acima, metade abaixo"],
                  ["P75", mi(base["pct"][75]), ""], ["P90", mi(base["pct"][90]), "10% acima"], ["P95", mi(base["pct"][95]), "5% acima"],
                  ["Média", mi(base["media"]), "puxada por poucas trajetórias muito boas"]])
tab_aloc = tabela(["Alocação (ações / públicos / privados)", "Retorno esp.", "Volatilidade", "P(meta R$ 5 mi)", "Mediana final", "P5 final", "P(queda > 30%)"],
                  [[f"{a['nome']} ({'/'.join(f'{x * 100:.0f}' for x in a['w'])})", pct(a["er"]), pct(a["vol"]), pct(a["p_meta"]),
                    mi(a["mediana"]), mi(a["pct"][5]), pct(a["p_dd30"])] for a in aloc_rows])
tab_dd = tabela(["Queda máxima em algum momento (pico → fundo)", "Probabilidade"],
                [["maior que 20%", pct(base["p_dd20"])], ["maior que 30%", pct(base["p_dd30"])], ["maior que 40%", pct(base["p_dd40"])],
                 ["Queda máxima mediana por trajetória", pct(base["dd_med"])]])
tab_est = tabela(["Cenário (ações −30%, −10%, 0% em 3 anos seguidos)", "Mediana final", "P10 final", "P(meta)"],
                 [["Sem choque (base)", mi(base["mediana"]), mi(base["pct"][10]), pct(base["p_meta"])],
                  ["Choque nos 3 primeiros anos (35 a 38)", mi(est_cedo["mediana"]), mi(est_cedo["pct"][10]), pct(est_cedo["p_meta"])],
                  ["Choque nos 3 últimos anos (62 a 65)", mi(est_tarde["mediana"]), mi(est_tarde["pct"][10]), pct(est_tarde["p_meta"])]])
tab_alav = tabela(["Alavanca", "O que seria necessário", "Observação"],
                  [["A. Aporte mensal", f"<strong>{brl(aporte_70)}</strong> (hoje {brl(mc.APORTE)}) para 70% de chance de R$ 5 mi", "mantém a alocação 60/30/10"],
                   ["B. Alocação + aporte", f"<strong>{brl(aporte_70_agr)}</strong> com 80/10/10", f"volatilidade {pct(mc.port_stats(W_AGR)[1])} e P(queda > 30%) de {pct(aloc_rows[3]['p_dd30'])}"],
                   ["C. Meta", f"Meta compatível com 70% de chance: <strong>{mi(meta_70)}</strong>", "mantém aporte e alocação"],
                   ["D. Horizonte", "Não simulado nesta versão", "depende de estender a janela de 30 anos"]], "")
tab_sens = tabela(["Premissa", "P(meta R$ 5 mi)", "Mediana final", "P10 final", "P(queda > 30%)"],
                  [[s["nome"], pct(s["p_meta"]), mi(s["mediana"]), mi(s["pct"][10]), pct(s["p_dd30"])] for s in sens])
tab_reb = tabela(["Estratégia (mesmas 10 mil trajetórias)", "Rebalanceamentos em 30 anos", "Mediana final", "P(meta)", "Queda máx. mediana", "P(queda > 30%)"],
                 [[r["nome"], num(r["ev"], 1), mi(r["mediana"]), pct(r["p_meta"]), pct(r["dd_med"]), pct(r["p_dd30"])] for r in reb])
tab_lin = tabela(["Classe", "Alvo", "Hoje", "Valor hoje", "Valor-alvo", "Ação", "Desvio", "Dispara banda de 5 p.p.?"], reb_lin)
tab_tat = tabela(["", "Estratégica 60/30/10", "Tática 65/25/10 (+5 p.p. em ações)"],
                 [["Retorno real esperado", pct(ret_p), pct(er_t)], ["Volatilidade", pct(vol_p), pct(vol_t)],
                  ["Mediana final", mi(base["mediana"]), mi(tat["mediana"])], ["P(queda > 30%)", pct(base["p_dd30"]), pct(tat["p_dd30"])],
                  ["P5 final", mi(base["pct"][5]), mi(tat["pct"][5])]])
tab_g1 = tabela(["Ano", "P5", "P25", "Mediana", "P75", "P95", "Retorno médio fixo"],
                [[i, mi(fan[5][i]), mi(fan[25][i]), mi(fan[50][i]), mi(fan[75][i]), mi(fan[95][i]), mi(det_path[::12][i])] for i in range(31)], "num small")

HTML = Path(__file__).with_name("simulacao_monte_carlo_template.html").read_text(encoding="utf-8")
subs = {
    "P_META": pct(base["p_meta"]), "MED": mi(base["mediana"]), "MEDIA": mi(base["media"]), "DET": mi(det_path[-1]),
    "APORTE70": brl(aporte_70), "META70": mi(meta_70), "RET": pct(ret_p), "VOL": pct(vol_p),
    "P10": mi(base["pct"][10]), "P90": mi(base["pct"][90]), "P5": mi(base["pct"][5]), "P95": mi(base["pct"][95]),
    "PDD30": pct(base["p_dd30"]), "PDD20": pct(base["p_dd20"]), "N": f"{mc.N:,}".replace(",", "."),
    "EST_CEDO": mi(est_cedo["mediana"]), "EST_TARDE": mi(est_tarde["mediana"]), "BASE_MED": mi(base["mediana"]),
    "TAB_PREM": tab_prem, "TAB_CORR": tab_corr, "TAB_PCT": tab_pct, "TAB_ALOC": tab_aloc, "TAB_DD": tab_dd, "TAB_EST": tab_est,
    "TAB_ALAV": tab_alav, "TAB_SENS": tab_sens, "TAB_REB": tab_reb, "TAB_LIN": tab_lin, "TAB_TAT": tab_tat, "TAB_G1": tab_g1,
    "G1": g1, "G2": g2, "G3": g3, "G4": g4,
    "REB_PDD_NENHUM": pct(reb[0]["p_dd30"]), "REB_PDD_ANUAL": pct(reb[1]["p_dd30"]), "REB_EV_BANDA": num(reb[2]["ev"], 1),
    "TAT_PDD": pct(tat["p_dd30"]), "TAT_VOL": pct(vol_t), "TAT_RET": pct(er_t), "EST_P10_CEDO": mi(est_cedo["pct"][10]),
    "AGR_PMETA": pct(aloc_rows[3]["p_meta"]), "AGR_PDD": pct(aloc_rows[3]["p_dd30"]), "ACOES_PMETA": pct(aloc_rows[4]["p_meta"]), "ACOES_PDD": pct(aloc_rows[4]["p_dd30"]),
    "SENS_MU": pct(sens[1]["p_meta"]), "SENS_VOL10": mi(sens[2]["pct"][10]), "BASE_P10": mi(base["pct"][10]),
    "SENS_T": pct(sens[3]["p_meta"]), "REB_ANUAL": mi(reb[1]["mediana"]), "REB_NENHUM": mi(reb[0]["mediana"]),
    "CHARTS_JSON": json.dumps(CHARTS, ensure_ascii=False),
}
out = HTML
for k, v in subs.items():
    out = out.replace(f"%%{k}%%", v)
Path(__file__).with_name("simulacao_monte_carlo.html").write_text(out, encoding="utf-8")

print("P(meta)", pct(base["p_meta"]), "| mediana", mi(base["mediana"]), "| aporte70", brl(aporte_70), "| aporte70 agressiva", brl(aporte_70_agr), "| meta70", mi(meta_70))
print("estresse cedo/tarde (mediana):", mi(est_cedo["mediana"]), mi(est_tarde["mediana"]))
for a in aloc_rows: print(a["nome"], pct(a["p_meta"]), pct(a["p_dd30"]), mi(a["mediana"]))
for s in sens: print(s["nome"], pct(s["p_meta"]), mi(s["mediana"]))
for r in reb: print(r["nome"], num(r["ev"], 1), mi(r["mediana"]), pct(r["p_meta"]), pct(r["dd_med"]), pct(r["p_dd30"]))
print("tático:", pct(er_t), pct(vol_t), mi(tat["mediana"]), pct(tat["p_dd30"]))
