#!/usr/bin/env python3
"""Gera um relatório de performance de exemplo (capítulo 6.3) em HTML.

TODOS OS DADOS SÃO FICTÍCIOS (simulados com semente fixa e calibrados com os
números do exercício 6.3.8). O objetivo é demonstrar que cada elemento citado
no texto pode ser calculado a partir de: (a) série de valor da carteira,
(b) fluxos de caixa (aportes/resgates), (c) retornos por classe e
(d) séries públicas de benchmark (CDI, IPCA, Ibovespa).

Uso:  python3 gerar_relatorio.py  ->  relatorio_exemplo.html
"""
import json
import math
import random
from pathlib import Path

random.seed(2026)

# ----------------------------------------------------------------------------
# 0. Parâmetros do plano (Bloco 1 do relatório)
# ----------------------------------------------------------------------------
PV0 = 200_000.0          # patrimônio inicial
APORTE = 1_500.0         # aporte mensal (em R$ do início do plano, reajustado pelo IPCA)
META = 1_000_000.0       # meta em R$ de poder de compra do início do plano
PRAZO_ANOS = 15
DD_TOLERADO = 0.08       # perda máxima tolerada (pico -> fundo)
PESOS = {"rf": 0.60, "acoes": 0.30, "mm": 0.10}            # carteira
PESOS_BENCH = {"rf": 0.55, "acoes": 0.35, "mm": 0.10}      # benchmark de política
N = 24                   # meses de histórico (nov/2024 a out/2026)
MESES_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
LABELS = []
y, m = 2024, 10  # índice de mês 0-based
for i in range(N):
    mm = (10 + i) % 12
    yy = 2024 + (10 + i) // 12
    LABELS.append(f"{MESES_PT[mm]}/{str(yy)[2:]}")
IDX_CHOQUE = 16          # mar/2026: choque de liquidez em ações
IDX_APORTE_EXTRA = 16    # aporte extra de R$ 40 mil (antes do choque)
IDX_RESGATE = 21         # resgate de R$ 15 mil em ago/2026


# ----------------------------------------------------------------------------
# 1. Utilidades numéricas
# ----------------------------------------------------------------------------
def pct(x, d=2, sign=False):
    s = f"{x * 100:+.{d}f}" if sign else f"{x * 100:.{d}f}"
    return s.replace(".", ",") + "%"


def pp(x, d=2):
    return f"{x * 100:+.{d}f}".replace(".", ",") + " p.p."


def brl(x):
    return "R$ " + f"{x:,.0f}".replace(",", ".")


def num(x, d=2):
    return f"{x:.{d}f}".replace(".", ",")


def comp(rs):
    p = 1.0
    for r in rs:
        p *= 1 + r
    return p - 1


def calibrar(ruido, alvo, ini, fim):
    """Soma um deslocamento constante ao ruído para que o retorno composto na
    janela [ini, fim) seja exatamente `alvo`."""
    lo, hi = -0.05, 0.05
    for _ in range(80):
        mid = (lo + hi) / 2
        r = comp([ruido[i] + mid for i in range(ini, fim)])
        lo, hi = (mid, hi) if r < alvo else (lo, mid)
    mid = (lo + hi) / 2
    return [ruido[i] + (mid if ini <= i < fim else 0) for i in range(len(ruido))]


def mean(x):
    return sum(x) / len(x)


def std(x):
    mu = mean(x)
    return math.sqrt(sum((v - mu) ** 2 for v in x) / (len(x) - 1))


def fv(pv, pmt, r_ano, n):
    i = (1 + r_ano) ** (1 / 12) - 1
    return pv * (1 + i) ** n + pmt * (((1 + i) ** n - 1) / i)


def retorno_necessario(pv, pmt, n, meta):
    lo, hi = -0.10, 0.60
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if fv(pv, pmt, mid, n) < meta else (lo, mid)
    return (lo + hi) / 2


def aporte_necessario(pv, r_ano, n, meta):
    i = (1 + r_ano) ** (1 / 12) - 1
    return (meta - pv * (1 + i) ** n) * i / ((1 + i) ** n - 1)


def meses_necessarios(pv, pmt, r_ano, meta, teto=600):
    for n in range(1, teto):
        if fv(pv, pmt, r_ano, n) >= meta:
            return n
    return None


# ----------------------------------------------------------------------------
# 2. Séries simuladas (fictícias)
# ----------------------------------------------------------------------------
def ruido(sigma):
    return [random.gauss(0, sigma) for _ in range(N)]


# IPCA e CDI (fictícios, calibrados com o exercício: ~4,2% a.a. de inflação)
ipca = calibrar(calibrar([0.0035 + v for v in ruido(0.0008)], 0.046, 0, 12), 0.042, 12, N)
cdi = calibrar(calibrar([0.0062 + v for v in ruido(0.0004)], 0.080, 0, 12), 0.076, 12, N)

# Ibovespa (choque em mar/26) e carteira de ações (menos correlacionada no período recente)
z_ibov = ruido(0.040)
z_ibov[IDX_CHOQUE] = -0.030
ibov = calibrar([0.008 + v for v in z_ibov], 0.110, 0, 12)
# janela recente: o benchmark de política (65% CDI + 35% Ibov) deve fechar em 8,2%
lo, hi = -0.05, 0.05
for _ in range(80):
    mid = (lo + hi) / 2
    cand = [ibov[i] + (mid if i >= 12 else 0) for i in range(N)]
    bench_try = comp([(PESOS_BENCH["rf"] + PESOS_BENCH["mm"]) * cdi[i] + PESOS_BENCH["acoes"] * cand[i] for i in range(12, N)])
    lo, hi = (mid, hi) if bench_try < 0.082 else (lo, mid)
ibov = [ibov[i] + ((lo + hi) / 2 if i >= 12 else 0) for i in range(N)]

z_acoes = [0.9 * z_ibov[i] + random.gauss(0, 0.015) for i in range(N)]
z_acoes[IDX_CHOQUE] = -0.085  # choque de liquidez em ativos específicos da carteira
acoes = calibrar(calibrar([0.008 + v for v in z_acoes], 0.105, 0, 12), 0.002, 12, N)

rf = calibrar(calibrar([0.0070 + v for v in ruido(0.0025)], 0.090, 0, 12), 0.095, 12, N)
mm = calibrar(calibrar([0.0075 + v for v in ruido(0.0040)], 0.094, 0, 12), 0.105, 12, N)

# Ajuste fino: renda fixa calibrada para que a carteira feche em 6,8% nominal nos últimos 12 meses
lo, hi = -0.02, 0.02
for _ in range(80):
    mid = (lo + hi) / 2
    cand = [rf[i] + (mid if i >= 12 else 0) for i in range(N)]
    rc = comp([PESOS["rf"] * cand[i] + PESOS["acoes"] * acoes[i] + PESOS["mm"] * mm[i] for i in range(12, N)])
    lo, hi = (mid, hi) if rc < 0.068 else (lo, mid)
rf = [rf[i] + ((lo + hi) / 2 if i >= 12 else 0) for i in range(N)]

# Carteira (rebalanceada mensalmente para 60/30/10) e benchmark de política
r_cart = [PESOS["rf"] * rf[i] + PESOS["acoes"] * acoes[i] + PESOS["mm"] * mm[i] for i in range(N)]
r_bench = [(PESOS_BENCH["rf"] + PESOS_BENCH["mm"]) * cdi[i] + PESOS_BENCH["acoes"] * ibov[i] for i in range(N)]

# ----------------------------------------------------------------------------
# 3. Fluxos de caixa e valor da carteira (aportes no início de cada mês)
# ----------------------------------------------------------------------------
fluxo = [APORTE * math.prod(1 + ipca[j] for j in range(i)) for i in range(N)]  # aporte reajustado
fluxo = [round(f, 2) for f in fluxo]
fluxo[IDX_APORTE_EXTRA] += 40_000
fluxo[IDX_RESGATE] -= 15_000
fluxo[0] += PV0  # patrimônio inicial entra no primeiro dia

valor_fim = []
v = 0.0
for i in range(N):
    v = (v + fluxo[i]) * (1 + r_cart[i])
    valor_fim.append(v)
V_AGORA = valor_fim[-1]

# Índices acumulados (base 100)
def indice(retornos):
    out, p = [100.0], 100.0
    for r in retornos:
        p *= 1 + r
        out.append(p)
    return out


idx_cart = indice(r_cart)
idx_bench = indice(r_bench)
idx_rf = indice(rf)
idx_acoes = indice(acoes)
idx_ipca = indice(ipca)

# ----------------------------------------------------------------------------
# 4. Retornos: TWR, MWR (TIR), real, por janela
# ----------------------------------------------------------------------------
def mwr_mensal(ini, fim):
    """TIR mensal dos fluxos (aportes no início do mês) com valor final no fim."""
    if ini == 0:
        v0, flows = 0.0, {i: fluxo[i] for i in range(0, fim)}
    else:
        v0, flows = valor_fim[ini - 1], {i: fluxo[i] for i in range(ini, fim)}
    n = fim - ini
    lo, hi = -0.05, 0.10
    for _ in range(100):
        mid = (lo + hi) / 2
        alvo = v0 * (1 + mid) ** n + sum(f * (1 + mid) ** (fim - i) for i, f in flows.items())
        lo, hi = (mid, hi) if alvo < valor_fim[fim - 1] else (lo, mid)
    return (lo + hi) / 2


def janela(ini, fim):
    twr = comp(r_cart[ini:fim])
    ben = comp(r_bench[ini:fim])
    inf = comp(ipca[ini:fim])
    n = fim - ini
    mwr_m = mwr_mensal(ini, fim)
    mwr = (1 + mwr_m) ** n - 1
    return {
        "twr": twr,
        "twr_real": (1 + twr) / (1 + inf) - 1,
        "bench": ben,
        "mwr": mwr,
        "ipca": inf,
        "n": n,
    }


JANELAS = {
    "Mês (out/26)": janela(N - 1, N),
    "Trimestre (ago–out/26)": janela(N - 3, N),
    "Ano corrente (jan–out/26)": janela(N - 10, N),
    "12 meses": janela(N - 12, N),
    "Desde o início (24 meses)": janela(0, N),
}
J12 = JANELAS["12 meses"]
JIN = JANELAS["Desde o início (24 meses)"]
anual_inicio = (1 + JIN["twr"]) ** (12 / 24) - 1
anual_inicio_real = (1 + anual_inicio) / (1 + (1 + JIN["ipca"]) ** 0.5 - 1) - 1

# ----------------------------------------------------------------------------
# 5. Risco: volatilidade, drawdown, Sharpe, Sortino, beta
# ----------------------------------------------------------------------------
def risco(ini, fim):
    r = r_cart[ini:fim]
    c = cdi[ini:fim]
    ib = ibov[ini:fim]
    vol = std(r) * math.sqrt(12)
    exc = [a - b for a, b in zip(r, c)]
    sharpe = (mean(exc) * 12) / vol if vol else float("nan")
    down = math.sqrt(mean([min(0, e) ** 2 for e in exc])) * math.sqrt(12)
    sortino = (mean(exc) * 12) / down if down else float("nan")
    mu_r, mu_i = mean(r), mean(ib)
    beta = sum((a - mu_r) * (b - mu_i) for a, b in zip(r, ib)) / sum((b - mu_i) ** 2 for b in ib)
    # drawdown sobre o índice acumulado da janela
    ind = indice(r)
    pico, dd_max, i_pico, i_fundo, rec = ind[0], 0.0, 0, 0, None
    atual_pico_i = 0
    for k, vv in enumerate(ind):
        if vv > pico:
            pico, atual_pico_i = vv, k
        dd = (pico - vv) / pico
        if dd > dd_max:
            dd_max, i_pico, i_fundo = dd, atual_pico_i, k
    # recuperação: primeiro mês após o fundo em que o índice volta ao pico
    pico_val = ind[i_pico]
    for k in range(i_fundo + 1, len(ind)):
        if ind[k] >= pico_val:
            rec = k - i_fundo
            break
    return {"vol": vol, "sharpe": sharpe, "sortino": sortino, "beta": beta,
            "dd": dd_max, "i_pico": i_pico + ini, "i_fundo": i_fundo + ini, "rec": rec}


R12 = risco(N - 12, N)
RIN = risco(0, N)
R_BENCH_VOL12 = std(r_bench[N - 12:]) * math.sqrt(12)

# série de drawdown (desde o início) para o gráfico
dd_serie, pico = [], idx_cart[0]
for vv in idx_cart:
    pico = max(pico, vv)
    dd_serie.append(-(pico - vv) / pico)

# ----------------------------------------------------------------------------
# 6. Atribuição de performance (últimos 12 meses): classe e Brinson-Fachler
# ----------------------------------------------------------------------------
CLASSES = [("rf", "Renda fixa indexada", rf, cdi), ("acoes", "Ações brasileiras", acoes, ibov),
           ("mm", "Multimercado crédito", mm, cdi)]
atrib = []
Rb_total_static = sum(PESOS_BENCH[k] * comp(b[N - 12:]) for k, _, _, b in CLASSES)
for k, nome, s_cart, s_bench in CLASSES:
    Rp_i = comp(s_cart[N - 12:])
    Rb_i = comp(s_bench[N - 12:])
    wp, wb = PESOS[k], PESOS_BENCH[k]
    atrib.append({
        "k": k, "nome": nome, "wp": wp, "wb": wb, "Rp": Rp_i, "Rb": Rb_i,
        "contrib": wp * Rp_i,
        "alocacao": (wp - wb) * (Rb_i - Rb_total_static),
        "selecao": wb * (Rp_i - Rb_i),
        "interacao": (wp - wb) * (Rp_i - Rb_i),
    })
soma_contrib = sum(a["contrib"] for a in atrib)
residuo = J12["twr"] - soma_contrib           # efeito composto/rebalanceamento mensal
bench_static = Rb_total_static
residuo_b = J12["bench"] - bench_static

# ----------------------------------------------------------------------------
# 7. Meta: retorno necessário, distância e cenários (em R$ reais do início do plano)
# ----------------------------------------------------------------------------
INFL_ACUM = 1 + JIN["ipca"]
V_REAL = V_AGORA / INFL_ACUM
R_NEC_INICIO = retorno_necessario(PV0, APORTE, PRAZO_ANOS * 12, META)   # desde o início do plano
N_REST = PRAZO_ANOS * 12 - N
R_NEC_AGORA = retorno_necessario(V_REAL, APORTE, N_REST, META)          # a partir de hoje
V_PLANO_AGORA = fv(PV0, APORTE, R_NEC_INICIO, N)                        # onde deveria estar
GAP = V_REAL - V_PLANO_AGORA

CEN = {"Pessimista": 0.025, "Realista": 0.045, "Otimista": 0.070}
proj_x = list(range(0, N_REST + 1, 6))
if proj_x[-1] != N_REST:
    proj_x.append(N_REST)
proj = {nome: [fv(V_REAL, APORTE, r, t) if t else V_REAL for t in proj_x] for nome, r in CEN.items()}
FIM_CEN = {nome: fv(V_REAL, APORTE, r, N_REST) for nome, r in CEN.items()}
APORTE_NEC = aporte_necessario(V_REAL, CEN["Realista"], N_REST, META)
MESES_EXTRA = meses_necessarios(V_REAL, APORTE, CEN["Realista"], META)
ANOS_EXTRA = (MESES_EXTRA - N_REST) / 12 if MESES_EXTRA else None
ANO_FIM_PLANO = 2024 + (10 + PRAZO_ANOS * 12) // 12  # ano em que o plano termina (nov/2039)

# ----------------------------------------------------------------------------
# 8. Geração de SVG (gráficos simples, um objetivo por gráfico)
# ----------------------------------------------------------------------------
CHARTS_JS = {}


def escala(vmin, vmax, a, b):
    return lambda v: a + (v - vmin) * (b - a) / (vmax - vmin)


def line_chart(cid, xlabels, series, ymin, ymax, yticks, yfmt, vfmt,
               hlines=(), band=None, area0=False, w=760, h=320, xtick_every=3, nudge=15, tick_labels=None):
    ml, mr, mt, mb = 56, 118, 14, 34
    X = escala(0, len(xlabels) - 1, ml, w - mr)
    Y = escala(ymin, ymax, h - mb, mt)
    o = [f'<svg class="chart" id="{cid}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="{cid}-t">']
    for t in yticks:
        o.append(f'<line x1="{ml}" x2="{w - mr}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" class="grid"/>')
        o.append(f'<text x="{ml - 8}" y="{Y(t) + 4:.1f}" class="tick" text-anchor="end">{yfmt(t)}</text>')
    for i, lab in enumerate(tick_labels or xlabels):
        if lab and (i % xtick_every == 0 or i == len(xlabels) - 1):
            o.append(f'<text x="{X(i):.1f}" y="{h - 12}" class="tick" text-anchor="middle">{lab}</text>')
    o.append(f'<line x1="{ml}" x2="{w - mr}" y1="{Y(0 if ymin < 0 < ymax else ymin):.1f}" y2="{Y(0 if ymin < 0 < ymax else ymin):.1f}" class="axis"/>')
    if band:
        lo_s, hi_s = band
        pts = [f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(series[hi_s]["vals"])]
        pts += [f"{X(i):.1f},{Y(v):.1f}" for i, v in reversed(list(enumerate(series[lo_s]["vals"])))]
        o.append(f'<polygon points="{" ".join(pts)}" class="band"/>')
    if area0:
        s = series[0]
        pts = [f"{X(0):.1f},{Y(0):.1f}"] + [f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(s["vals"])] + [f"{X(len(s['vals']) - 1):.1f},{Y(0):.1f}"]
        o.append(f'<polygon points="{" ".join(pts)}" class="area" style="fill:var({s["color"]})"/>')
    for hv, hl in hlines:
        o.append(f'<line x1="{ml}" x2="{w - mr}" y1="{Y(hv):.1f}" y2="{Y(hv):.1f}" class="ref"/>')
        o.append(f'<text x="{ml + 8}" y="{Y(hv) - 6:.1f}" class="dlabel" style="fill:var(--ink2)">{hl}</text>')
    labels_y = []
    for s in series:
        d = " ".join(f"{'M' if i == 0 else 'L'}{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(s["vals"]))
        dash = f' stroke-dasharray="{s["dash"]}"' if s.get("dash") else ""
        sw = s.get("sw", 2)
        o.append(f'<path d="{d}" fill="none" stroke="var({s["color"]})" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round"{dash}/>')
        labels_y.append([Y(s["vals"][-1]), s])
    # rótulos diretos no fim das linhas, sem colisão
    labels_y.sort(key=lambda t: t[0])
    for k in range(1, len(labels_y)):
        if labels_y[k][0] - labels_y[k - 1][0] < nudge:
            labels_y[k][0] = labels_y[k - 1][0] + nudge
    for yy, s in labels_y:
        o.append(f'<text x="{w - mr + 6}" y="{yy + 4:.1f}" class="dlabel">{s["name"]}</text>')
    o.append('<line class="xhair" y1="%d" y2="%d" x1="0" x2="0" visibility="hidden"/>' % (mt, h - mb))
    for _ in series:
        o.append('<circle class="dot" r="4" visibility="hidden"/>')
    o.append(f'<rect class="hit" x="{ml}" y="{mt}" width="{w - ml - mr}" height="{h - mt - mb}" fill="transparent"/>')
    o.append("</svg>")
    CHARTS_JS[cid] = {
        "w": w,
        "xs": [round(X(i), 1) for i in range(len(xlabels))],
        "xlabels": xlabels,
        "series": [{"name": s["name"], "color": s["color"],
                    "ys": [round(Y(v), 1) for v in s["vals"]],
                    "txt": [vfmt(v) for v in s["vals"]]} for s in series],
    }
    return "\n".join(o)


def bar_chart(cid, items, vmin, vmax, w=760, rowh=46):
    """Barras horizontais (contribuição por classe, em p.p.)."""
    ml, mr, mt = 170, 70, 10
    h = mt + rowh * len(items) + 30
    X = escala(vmin, vmax, ml, w - mr)
    o = [f'<svg class="chart" id="{cid}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="{cid}-t">']
    for t in range(int(vmin), int(vmax) + 1):
        o.append(f'<line x1="{X(t):.1f}" x2="{X(t):.1f}" y1="{mt}" y2="{h - 26}" class="grid"/>')
        o.append(f'<text x="{X(t):.1f}" y="{h - 8}" class="tick" text-anchor="middle">{t} p.p.</text>')
    x0 = X(0)
    for i, (nome, val, txt) in enumerate(items):
        y0 = mt + i * rowh + 8
        x1, x2 = (x0, X(val)) if val >= 0 else (X(val), x0)
        o.append(f'<text x="{ml - 12}" y="{y0 + 16}" class="dlabel" text-anchor="end" style="fill:var(--ink)">{nome}</text>')
        o.append(f'<rect x="{x1:.1f}" y="{y0}" width="{max(x2 - x1, 1.5):.1f}" height="22" rx="3" fill="var(--s1)"><title>{nome}: {txt}</title></rect>')
        tx = x2 + 8 if val >= 0 else x1 - 8
        o.append(f'<text x="{tx:.1f}" y="{y0 + 16}" class="dlabel" style="fill:var(--ink)" text-anchor="{"start" if val >= 0 else "end"}">{txt}</text>')
    o.append(f'<line x1="{x0:.1f}" x2="{x0:.1f}" y1="{mt}" y2="{h - 26}" class="axis"/>')
    o.append("</svg>")
    return "\n".join(o)


def tabela(cab, linhas, cls=""):
    h = "".join(f"<th>{c}</th>" for c in cab)
    r = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in l) + "</tr>" for l in linhas)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{r}</tbody></table></div>'


# --- Gráfico 1: trajetória acumulada (base 100) vs linha de retorno necessário
xl = ["início"] + LABELS
idx_meta = [100.0]
for i in range(N):
    idx_meta.append(idx_meta[-1] * (1 + R_NEC_INICIO) ** (1 / 12) * (1 + ipca[i]))
g1_vals = idx_cart + idx_meta + idx_rf + idx_acoes
g1 = line_chart(
    "g1", xl,
    [{"name": "Carteira", "vals": idx_cart, "color": "--s1", "sw": 2.5},
     {"name": "Necessário p/ meta", "vals": idx_meta, "color": "--s2", "dash": "6 4"},
     {"name": "100% renda fixa", "vals": idx_rf, "color": "--mut", "sw": 1.5},
     {"name": "100% ações", "vals": idx_acoes, "color": "--mut", "sw": 1.5, "dash": "2 3"}],
    90, 135, [90, 100, 110, 120, 130], lambda t: f"{t:.0f}", lambda v: num(v, 1), xtick_every=4)

# --- Gráfico 2: faixa de viabilidade (R$ mil reais)
xl2 = [f"+{x // 12} anos" if x % 12 == 0 else f"+{x / 12:.1f} anos".replace(".", ",") for x in proj_x]
xl2_ticks = [("+" + str(x // 12) + "a") if x % 12 == 0 else "" for x in proj_x]
g2 = line_chart(
    "g2", xl2,
    [{"name": f"Pessimista ({pct(CEN['Pessimista'], 1)})", "vals": [v / 1000 for v in proj["Pessimista"]], "color": "--mut", "sw": 1.5},
     {"name": f"Realista ({pct(CEN['Realista'], 1)})", "vals": [v / 1000 for v in proj["Realista"]], "color": "--s1", "sw": 2.5},
     {"name": f"Otimista ({pct(CEN['Otimista'], 1)})", "vals": [v / 1000 for v in proj["Otimista"]], "color": "--mut", "sw": 1.5, "dash": "2 3"}],
    0, 1300, [0, 250, 500, 750, 1000, 1250], lambda t: f"{t:,.0f}".replace(",", "."), lambda v: "R$ " + f"{v:,.0f} mil".replace(",", "."),
    hlines=[(META / 1000, "Meta: R$ 1 mi")], band=(0, 2), h=330, xtick_every=1, w=760, nudge=15, tick_labels=xl2_ticks)

# --- Gráfico 3: contribuição por classe (12 meses, p.p.)
itens = [(a["nome"], a["contrib"] * 100, pp(a["contrib"], 2).replace(" p.p.", " p.p.")) for a in atrib]
g3 = bar_chart("g3", itens, 0, 6)

# --- Gráfico 4: drawdown
g4 = line_chart(
    "g4", xl, [{"name": "Drawdown", "vals": [d * 100 for d in dd_serie], "color": "--s1", "sw": 2}],
    -10, 0, [-10, -8, -6, -4, -2, 0], lambda t: f"{t:.0f}%", lambda v: num(v, 2) + "%",
    hlines=[(-DD_TOLERADO * 100, "Limite −8%")], area0=True, h=240, xtick_every=4)

# ----------------------------------------------------------------------------
# 9. Texto e tabelas
# ----------------------------------------------------------------------------
atras = R_NEC_INICIO - J12["twr_real"]
status_txt = "Abaixo do ritmo necessário"
rec_txt = (f"{R12['rec']} mês(es) para recuperar" if R12["rec"] else "ainda em recuperação")

tab_ret = tabela(
    ["Período", "Carteira (TWR)", "Carteira real", "Benchmark", "vs. benchmark", "MWR (TIR do cliente)"],
    [[nome, pct(j["twr"]), pct(j["twr_real"]), pct(j["bench"]), pp(j["twr"] - j["bench"]),
      pct(j["mwr"]) if j["n"] >= 3 else "—"] for nome, j in JANELAS.items()], "num")

tab_risco = tabela(
    ["Métrica", "12 meses", "Desde o início", "Como ler"],
    [["Volatilidade anualizada", pct(R12["vol"]), pct(RIN["vol"]), "desvio-padrão mensal × √12"],
     ["Drawdown máximo", pct(-R12["dd"]), pct(-RIN["dd"]), f"limite tolerado: {pct(-DD_TOLERADO, 0)}"],
     ["Tempo de recuperação", "—", rec_txt, "do fundo até o pico anterior"],
     ["Índice de Sharpe", num(R12["sharpe"]), num(RIN["sharpe"]), "excesso sobre o CDI ÷ volatilidade (negativo = rendeu menos que o CDI)"],
     ["Índice de Sortino", num(R12["sortino"]), num(RIN["sortino"]), "só penaliza volatilidade negativa"],
     ["Beta vs. Ibovespa", num(R12["beta"]), num(RIN["beta"]), "sensibilidade a movimentos do índice"]], "num")

tab_atrib = tabela(
    ["Classe", "Peso cart.", "Peso bench.", "Ret. cart.", "Ret. índice", "Contrib.", "Aloc.", "Seleção", "Inter."],
    [[a["nome"], pct(a["wp"], 0), pct(a["wb"], 0), pct(a["Rp"]), pct(a["Rb"]), pp(a["contrib"]),
      pp(a["alocacao"]), pp(a["selecao"]), pp(a["interacao"])] for a in atrib]
    + [["<strong>Total</strong>", "100%", "100%", f"<strong>{pct(J12['twr'])}</strong>", f"<strong>{pct(J12['bench'])}</strong>",
        f"<strong>{pp(soma_contrib)}</strong>", f"<strong>{pp(sum(a['alocacao'] for a in atrib))}</strong>",
        f"<strong>{pp(sum(a['selecao'] for a in atrib))}</strong>", f"<strong>{pp(sum(a['interacao'] for a in atrib))}</strong>"]], "num small")

ajuste_linhas = [
    ["A. Aumentar o retorno", f"Retorno real necessário a partir de hoje: <strong>{pct(R_NEC_AGORA)} a.a.</strong> (hoje a carteira entrega {pct(J12['twr_real'])} real)", "Exige mais risco — só se o perfil permitir"],
    ["B. Aumentar o aporte", f"Com retorno real de {pct(CEN['Realista'], 1)}, aporte mensal de <strong>{brl(APORTE_NEC)}</strong> (hoje {brl(APORTE)})", "Não depende de mercado"],
    ["C. Estender o prazo", f"Com {pct(CEN['Realista'], 1)} real e aporte atual, a meta é atingida em <strong>~{ANOS_EXTRA + PRAZO_ANOS:.1f} anos</strong> do início (prazo original: {PRAZO_ANOS})" if ANOS_EXTRA is not None else "—", "Ajuste de horizonte"],
]
tab_ajuste = tabela(["Alavanca", "O que seria necessário", "Observação"], ajuste_linhas)

tab_cen = tabela(
    ["Cenário (retorno real a.a.)", "Patrimônio ao fim do prazo (R$ de hoje)", "Meta atingida?"],
    [[f"{n} ({pct(r, 1)})", brl(FIM_CEN[n]), "Sim" if FIM_CEN[n] >= META else f"Não (faltam {brl(META - FIM_CEN[n])})"]
     for n, r in CEN.items()], "num")

# tabelas alternativas (acessibilidade): dados dos gráficos
tab_g1 = tabela(["Mês", "Carteira", "Necessário p/ meta", "100% renda fixa", "100% ações"],
                [[xl[i], num(idx_cart[i], 1), num(idx_meta[i], 1), num(idx_rf[i], 1), num(idx_acoes[i], 1)] for i in range(N + 1)], "num small")
tab_g4 = tabela(["Mês", "Drawdown"], [[xl[i], num(dd_serie[i] * 100, 2) + "%"] for i in range(N + 1)], "num small")
tab_g2 = tabela(["Horizonte"] + list(CEN),
                [[xl2[i]] + [brl(proj[n][i]) for n in CEN] for i in range(len(proj_x))], "num small")

# ----------------------------------------------------------------------------
# 10. Template HTML
# ----------------------------------------------------------------------------
HTML = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Relatório de Performance — Exemplo</title>
<style>
:root{
  --bg:#f9f9f7; --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --mut:#898781;
  --grid:#e1e0d9; --axis:#c3c2b7; --line:rgba(11,11,11,.10);
  --s1:#2a78d6; --s2:#eb6834; --band:rgba(42,120,214,.10);
  color-scheme:light;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#0d0d0d; --surface:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --mut:#898781;
    --grid:#2c2c2a; --axis:#383835; --line:rgba(255,255,255,.10);
    --s1:#3987e5; --s2:#d95926; --band:rgba(57,135,229,.16); color-scheme:dark;
  }
}
:root[data-theme="dark"]{
  --bg:#0d0d0d; --surface:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --mut:#898781;
  --grid:#2c2c2a; --axis:#383835; --line:rgba(255,255,255,.10);
  --s1:#3987e5; --s2:#d95926; --band:rgba(57,135,229,.16); color-scheme:dark;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:860px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:1.6rem;line-height:1.2;margin:0 0 4px}
h2{font-size:1.25rem;margin:40px 0 4px}
h3{font-size:1.02rem;margin:26px 0 6px}
p{margin:8px 0}
.sub{color:var(--ink2);margin:0 0 16px}
.aviso{border:1px solid var(--line);border-left:4px solid var(--s2);background:var(--surface);padding:12px 14px;border-radius:8px;font-size:.92rem;color:var(--ink2)}
.card{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:16px;margin:12px 0}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:16px 0}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:14px}
.kpi .l{font-size:.8rem;color:var(--ink2)}
.kpi .v{font-size:1.65rem;font-weight:650;line-height:1.2;margin:2px 0}
.kpi .n{font-size:.82rem;color:var(--ink2)}
.q{display:inline-block;font-size:.72rem;font-weight:650;letter-spacing:.04em;text-transform:uppercase;color:var(--ink2);margin-top:28px}
.chart{width:100%;height:auto;display:block;overflow:visible}
.grid{stroke:var(--grid);stroke-width:1}
.axis{stroke:var(--axis);stroke-width:1}
.ref{stroke:var(--ink2);stroke-width:1;stroke-dasharray:4 4}
.tick{fill:var(--mut);font-size:11px;font-variant-numeric:tabular-nums}
.dlabel{fill:var(--ink);font-size:12px}
.band{fill:var(--band)}
.area{opacity:.16}
.xhair{stroke:var(--axis);stroke-width:1}
.dot{fill:var(--surface);stroke-width:2}
.wrap{position:relative}
.tip{position:absolute;pointer-events:none;background:var(--surface);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:.8rem;box-shadow:0 4px 16px rgba(0,0,0,.14);display:none;z-index:2;white-space:nowrap}
.tip b{display:block;margin-bottom:2px}
.tip i{display:inline-block;width:10px;height:3px;border-radius:2px;margin-right:6px;vertical-align:middle}
.leg{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:.82rem;color:var(--ink2);margin:6px 0 0}
.leg i{display:inline-block;width:14px;height:3px;border-radius:2px;margin-right:6px;vertical-align:middle}
.tw{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:.88rem}
th,td{padding:7px 10px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:600;color:var(--ink2);font-size:.78rem;white-space:nowrap}
table.num td:not(:first-child){font-variant-numeric:tabular-nums}
table.small{font-size:.8rem}
details{margin:8px 0}
summary{cursor:pointer;color:var(--ink2);font-size:.85rem}
ul{padding-left:20px;margin:8px 0}
li{margin:5px 0}
.pill{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:1px 10px;font-size:.78rem;color:var(--ink2)}
footer{margin-top:40px;color:var(--ink2);font-size:.8rem}
@media (max-width:520px){h1{font-size:1.35rem}.kpi .v{font-size:1.4rem}}
</style>
</head>
<body>
<main>

<p class="sub">Exemplo de relatório · Cliente fictício · Posição em 31/out/2026</p>
<h1>Relatório de performance — Plano R$ 1 milhão</h1>
<div class="aviso"><strong>Dados fictícios.</strong> Todos os números foram simulados e calibrados com o exercício 6.3.8 para demonstrar a estrutura. Eles não representam mercado, cliente ou recomendação reais.</div>

<span class="q">Resumo — as três perguntas</span>
<div class="kpis">
  <div class="kpi"><div class="l">1 · Onde estou frente à meta?</div><div class="v">%%PCT_META%%</div><div class="n">%%V_REAL%% em R$ de hoje, de %%META%%. A trajetória do plano pedia %%V_PLANO%%: %%GAP_TXT%%</div></div>
  <div class="kpi"><div class="l">2 · O que move a trajetória?</div><div class="v">%%R12_REAL%% real</div><div class="n">nos 12 meses, contra %%R_NEC%% necessários. Renda fixa e multimercado entregaram; ações ficaram em %%R_ACOES%%.</div></div>
  <div class="kpi"><div class="l">3 · O que decidir?</div><div class="v">Ajuste de rota</div><div class="n">Aumentar aporte, prazo ou retorno (opções no bloco 3). Perda máxima de %%DD12%% está dentro do limite de %%DDTOL%%.</div></div>
</div>
<p><span class="pill">⚠ %%STATUS%%</span> O retorno real de %%R12_REAL%% está abaixo dos %%R_NEC%% a.a. exigidos desde o início do plano. Esta defasagem é o ponto de atenção, não a comparação com o benchmark.</p>

<h2>1. Contexto do plano de investimento</h2>
<p class="sub">O objetivo convertido em parâmetros técnicos.</p>
%%TAB_CTX%%

<h2>2. Evolução da performance em relação à meta</h2>
<h3 id="g1-t">Trajetória da carteira vs. retorno necessário (base 100, nominal)</h3>
<p class="sub">A carteira está %%ATRAS%% por ano abaixo do ritmo que levaria à meta. Linhas de referência (100% renda fixa e 100% ações) são apenas ilustrativas.</p>
<div class="card wrap" data-chart="g1">%%G1%%<div class="tip"></div></div>
<details><summary>Ver dados do gráfico</summary>%%TAB_G1%%</details>

<h3 id="g2-t">Faixa de viabilidade da meta (R$ mil de hoje)</h3>
<p class="sub">Projeção a partir de hoje, %%N_REST_ANOS%% anos restantes, aporte atual reajustado pela inflação. A faixa sombreada vai do cenário pessimista ao otimista (retorno real anual).</p>
<div class="card wrap" data-chart="g2">%%G2%%<div class="tip"></div></div>
%%TAB_CEN%%
<details><summary>Ver dados do gráfico</summary>%%TAB_G2%%</details>

<h2>3. Análise técnica e recomendações</h2>

<h3>3.1 Retorno por período e metodologia</h3>
<p class="sub">TWR remove o efeito de aportes e resgates e avalia a gestão. MWR (TIR) mostra o que o cliente de fato ganhou, dado o momento dos aportes. A diferença entre os dois é informação: aqui ela vem do aporte extra de R$ 40 mil (mar/26) e do resgate de R$ 15 mil (ago/26).</p>
%%TAB_RET%%

<h3>3.2 Retorno necessário × retorno atual</h3>
%%TAB_NEC%%

<h3>3.3 Risco</h3>
%%TAB_RISCO%%
<h3 id="g4-t">Drawdown desde o início</h3>
<p class="sub">Perda máxima de %%DDIN%% (em %%DD_FUNDO%%), %%REC%%. Limite do cliente: %%DDTOL%%.</p>
<div class="card wrap" data-chart="g4">%%G4%%<div class="tip"></div></div>
<details><summary>Ver dados do gráfico</summary>%%TAB_G4%%</details>

<h3 id="g3-t">De onde veio o retorno (contribuição por classe, 12 meses)</h3>
<p class="sub">Contribuição = peso × retorno da classe. Soma %%SOMA_CONTRIB%% do retorno da carteira de %%R12%%; a diferença (%%RESIDUO%%) é efeito de rebalanceamento mensal.</p>
<div class="card">%%G3%%</div>

<h3>3.4 Decomposição: alocação × seleção</h3>
<p class="sub">Brinson-Fachler contra o benchmark de política (55% CDI, 35% Ibovespa, 10% CDI). Alocação mede o efeito dos pesos; seleção, dos ativos dentro de cada classe.</p>
%%TAB_ATRIB%%
<p>Leitura: a renda fixa e o multimercado superaram seus índices (%%SEL_POS%% de seleção). O resultado abaixo do benchmark vem quase todo da <strong>seleção em ações</strong> (%%SEL_ACOES%%), concentrada no choque de liquidez de mar/26.</p>

<h3>3.5 Recomendações para o consultor revisar</h3>
<ul>
  <li><strong>Não aumentar ações só para alcançar o benchmark.</strong> A defasagem relevante é frente à meta (%%ATRAS%% ao ano), não frente ao índice (%%GAP_BENCH%%).</li>
  <li><strong>Investigar a seleção em ações:</strong> quais papéis/fundos sofreram no choque de liquidez e se o problema é pontual ou estrutural.</li>
  <li><strong>Escolher a alavanca de ajuste</strong> (tabela abaixo). Se o padrão se repetir por mais 12 meses, a revisão do plano deixa de ser opcional.</li>
  <li><strong>Manter a disciplina de risco:</strong> drawdown máximo de %%DD12%% está dentro do limite tolerado.</li>
</ul>
%%TAB_AJUSTE%%

<h2>Metodologia e premissas</h2>
<ul>
  <li><strong>Retorno necessário:</strong> taxa real que leva R$ 200 mil + R$ 1.500/mês (reajustados pelo IPCA) a R$ 1.000.000 em 15 anos; calculado, não estimado: <strong>%%R_NEC%% a.a.</strong> desde o início e <strong>%%R_NEC_AGORA%% a.a.</strong> a partir de hoje.</li>
  <li><strong>TWR:</strong> produto dos retornos mensais. <strong>MWR:</strong> TIR dos fluxos mensais, anualizada na janela.</li>
  <li><strong>Real:</strong> deflacionado pelo IPCA do exemplo. Retornos tratados como líquidos de custos e impostos.</li>
  <li><strong>Risco:</strong> volatilidade = desvio-padrão mensal × √12. Sharpe/Sortino sobre o CDI. Beta por regressão mensal contra o Ibovespa. Drawdown sobre o índice acumulado mensal.</li>
  <li><strong>Simplificações do exemplo:</strong> granularidade mensal, aportes no início do mês, rebalanceamento mensal para 60/30/10, projeções com aportes ao fim do mês. Com dados reais recomenda-se valor diário.</li>
  <li>Rentabilidade passada não garante rentabilidade futura. Projeções são cenários, não promessas.</li>
</ul>
<footer>Gerado por <code>relatorio/gerar_relatorio.py</code> · dados simulados com semente fixa · conteúdo para revisão do consultor antes de qualquer envio ao cliente.</footer>
</main>

<script>
const CH = %%CHARTS_JSON%%;
document.querySelectorAll('.wrap[data-chart]').forEach(box=>{
  const id=box.dataset.chart, cfg=CH[id], svg=box.querySelector('svg'), tip=box.querySelector('.tip');
  const xh=svg.querySelector('.xhair'), dots=[...svg.querySelectorAll('.dot')], hit=svg.querySelector('.hit');
  const css=n=>getComputedStyle(document.documentElement).getPropertyValue(n);
  function move(e){
    const r=svg.getBoundingClientRect(), sc=cfg.w/r.width, x=(e.clientX-r.left)*sc;
    let k=0,b=1e9; cfg.xs.forEach((v,i)=>{const d=Math.abs(v-x); if(d<b){b=d;k=i}});
    xh.setAttribute('x1',cfg.xs[k]); xh.setAttribute('x2',cfg.xs[k]); xh.setAttribute('visibility','visible');
    let html='<b>'+cfg.xlabels[k]+'</b>';
    cfg.series.forEach((s,j)=>{
      dots[j].setAttribute('cx',cfg.xs[k]); dots[j].setAttribute('cy',s.ys[k]);
      dots[j].setAttribute('stroke',css(s.color)); dots[j].setAttribute('visibility','visible');
      html+='<div><i style="background:'+css(s.color)+'"></i>'+s.name+': '+s.txt[k]+'</div>';
    });
    tip.innerHTML=html; tip.style.display='block';
    const bx=box.getBoundingClientRect(), px=cfg.xs[k]/sc+(r.left-bx.left);
    const tw=tip.offsetWidth; tip.style.left=Math.min(Math.max(px+12,4),bx.width-tw-4)+'px'; tip.style.top='12px';
  }
  function leave(){xh.setAttribute('visibility','hidden');dots.forEach(d=>d.setAttribute('visibility','hidden'));tip.style.display='none'}
  hit.addEventListener('pointermove',move); hit.addEventListener('pointerleave',leave);
});
</script>
</body>
</html>
"""

tab_ctx = tabela(
    ["Parâmetro", "Valor"],
    [["Objetivo", f"{brl(META)} em {PRAZO_ANOS} anos (poder de compra do início do plano)"],
     ["Patrimônio inicial / aporte mensal", f"{brl(PV0)} / {brl(APORTE)} (reajustado pelo IPCA)"],
     ["Retorno real necessário", f"<strong>{pct(R_NEC_INICIO)} a.a.</strong> desde o início · <strong>{pct(R_NEC_AGORA)} a.a.</strong> a partir de hoje"],
     ["Perfil e tolerância", f"Moderado · perda máxima tolerada de {pct(DD_TOLERADO, 0)}"],
     ["Alocação-alvo", "60% renda fixa indexada · 30% ações Brasil · 10% multimercado crédito"],
     ["Liquidez e tributação", "Reserva de emergência fora da carteira · retornos líquidos de IR (premissa do exemplo)"]])

tab_nec = tabela(
    ["", "Valor"],
    [["Retorno real necessário (desde o início do plano)", f"<strong>{pct(R_NEC_INICIO)} a.a.</strong>"],
     [f"Retorno real atual (12 meses)", f"<strong>{pct(J12['twr_real'])}</strong>"],
     ["Retorno real atual (anualizado desde o início)", pct(anual_inicio_real)],
     ["Defasagem", f"{pp(J12['twr_real'] - R_NEC_INICIO)} ao ano"],
     ["Ajuste de rota", "ver alavancas abaixo"]], "num") + "<br>"

subs = {
    "PCT_META": pct(V_REAL / META, 1) + " da meta",
    "V_REAL": brl(V_REAL), "META": brl(META), "V_PLANO": brl(V_PLANO_AGORA),
    "GAP_TXT": (f"você está {brl(abs(GAP))} à frente, mas por causa do aporte extra, não do retorno." if GAP >= 0 else f"você está {brl(abs(GAP))} atrás."),
    "R12_REAL": pct(J12["twr_real"]), "R_NEC": pct(R_NEC_INICIO), "R_NEC_AGORA": pct(R_NEC_AGORA),
    "R_ACOES": pct(atrib[1]["Rp"]), "DD12": pct(R12["dd"]), "DDIN": pct(RIN["dd"]), "DDTOL": pct(DD_TOLERADO, 0),
    "STATUS": status_txt, "ATRAS": pp(abs(atras)).replace(" p.p.", " p.p."),
    "N_REST_ANOS": f"{N_REST / 12:.0f}", "REC": rec_txt, "DD_FUNDO": LABELS[RIN["i_fundo"] - 1] if RIN["i_fundo"] > 0 else "—",
    "SOMA_CONTRIB": pp(soma_contrib).replace(" p.p.", " p.p."), "R12": pct(J12["twr"]), "RESIDUO": pp(residuo),
    "SEL_POS": pp(atrib[0]["selecao"] + atrib[2]["selecao"]), "SEL_ACOES": pp(atrib[1]["selecao"]),
    "GAP_BENCH": pp(J12["twr"] - J12["bench"]),
    "TAB_CTX": tab_ctx, "TAB_NEC": tab_nec, "TAB_RET": tab_ret, "TAB_RISCO": tab_risco, "TAB_ATRIB": tab_atrib,
    "TAB_AJUSTE": tab_ajuste, "TAB_CEN": tab_cen, "TAB_G1": tab_g1, "TAB_G2": tab_g2, "TAB_G4": tab_g4,
    "G1": g1, "G2": g2, "G3": g3, "G4": g4,
    "CHARTS_JSON": json.dumps(CHARTS_JS, ensure_ascii=False),
}
out = HTML
for k, val in subs.items():
    out = out.replace(f"%%{k}%%", val)

destino = Path(__file__).with_name("relatorio_exemplo.html")
destino.write_text(out, encoding="utf-8")

# Resumo no terminal para conferência
print("12m: carteira", pct(J12["twr"]), "| real", pct(J12["twr_real"]), "| bench", pct(J12["bench"]), "| IPCA", pct(J12["ipca"]))
print("MWR 12m", pct(J12["mwr"]), "| desde início TWR", pct(JIN["twr"]), "MWR", pct(JIN["mwr"]))
print("vol12", pct(R12["vol"]), "dd12", pct(R12["dd"]), "sharpe", num(R12["sharpe"]), "sortino", num(R12["sortino"]), "beta", num(R12["beta"]))
print("ddIN", pct(RIN["dd"]), "rec", RIN["rec"], "fundo", LABELS[RIN["i_fundo"] - 1] if RIN["i_fundo"] else None)
print("R nec inicio", pct(R_NEC_INICIO), "agora", pct(R_NEC_AGORA), "V_real", brl(V_REAL), "plano", brl(V_PLANO_AGORA), "gap", brl(GAP))
print("contrib", [pp(a["contrib"]) for a in atrib], "residuo", pp(residuo))
print("aporte nec", brl(APORTE_NEC), "anos total", (MESES_EXTRA + N) / 12 if MESES_EXTRA else None, "fim cenarios", {k: brl(v) for k, v in FIM_CEN.items()})
print("escrito:", destino)
