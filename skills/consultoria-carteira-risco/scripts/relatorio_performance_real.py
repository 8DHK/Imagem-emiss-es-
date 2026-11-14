#!/usr/bin/env python3
"""Relatório de performance com DADOS REAIS, no formato do cap. 6.3 (contexto, evolução vs meta, análise).

Uso:  python3 relatorio_performance_real.py config.json saida.html
Entrada: um config.json montado a partir dos relatórios do custodiante (nunca versionar). Campos:
  titulo, subtitulo, data_base, escopo (texto do que o cálculo cobre),
  plano: {retirada_mensal, idade, ate_idade, patrimonio_ref, tolerancia_drawdown (ou null = a combinar),
          benchmarks: [{nome, spread_real}]}          # ex.: IPCA+4, IPCA+6; spread_real em fração
  meses: [{rotulo, pat_ini, mov, impostos, pat_fim, ganho, ret, cdi, ipca}]   # ret/cdi/ipca em fração
  fluxo_meio_do_mes: true  (premissa de data dos fluxos para o MWR)
  posicoes: [{nome, classe, valor, ganho_acum}]  | encerradas_ganho (ganho de posições encerradas)
  limites: {classes:[[classe, atual, min, max]], alertas:[texto]}
  liquidez: [[faixa, pct, valor]]
  extras: [{titulo, texto, tabela:{cab, linhas}}]   fontes: [[dado, valor, origem]]      pendencias: [texto]
Calcula TWR, MWR, volatilidade, drawdown, Sharpe, Sortino, retorno necessário e contribuição por classe. Beta só se `serie_indice`
(retornos mensais do índice) for informada; caso contrário aparece como pendente.
"""
import json
import math
import sys
from pathlib import Path

CFG = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
SAIDA = Path(sys.argv[2])


def pct(x, d=2, sinal=False):
    s = f"{x * 100:+.{d}f}" if sinal else f"{x * 100:.{d}f}"
    return s.replace(".", ",") + "%"
def brl(x): return ("-" if x < 0 else "") + "R$ " + f"{abs(x):,.0f}".replace(",", ".")
def brl2(x): return ("-" if x < 0 else "") + "R$ " + f"{abs(x):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
def num(x, d=2): return f"{x:.{d}f}".replace(".", ",")
def pp(x, d=2): return f"{x * 100:+.{d}f}".replace(".", ",") + " p.p."
def mean(x): return sum(x) / len(x)
def std(x): m = mean(x); return math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1))
def comp(r):
    p = 1.0
    for v in r: p *= 1 + v
    return p - 1


M = CFG["meses"]
N = len(M)
R = [m["ret"] if m.get("ret") is not None else m["ganho"] / (m["pat_ini"] + m["mov"] / 2 if m["pat_ini"] else m["mov"]) for m in M]
CDI = [m["cdi"] for m in M]
IPCA = [m["ipca"] for m in M]
LAB = [m["rotulo"] for m in M]
PL = CFG["plano"]
W, IDADE, ATE = PL["retirada_mensal"], PL["idade"], PL["ate_idade"]
PV = PL["patrimonio_ref"]
ANOS = ATE - IDADE


# ------------------------------------------------------------------ cálculos do livro
def capital_mensal(r, w, anos):
    i = (1 + r) ** (1 / 12) - 1
    n = anos * 12
    return w * (1 - (1 + i) ** -n) / i * (1 + i)          # retirada no início do mês


def retorno_necessario(pv, w, anos):
    lo, hi = -0.05, 0.40
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if capital_mensal(mid, w, anos) > pv else (lo, mid)
    return (lo + hi) / 2


R_NEC = retorno_necessario(PV, W, ANOS)
BENCH = PL.get("benchmarks", [])


def fator_real(spread, ipca):                              # IPCA + spread, mensal
    return [(1 + p) * (1 + spread) ** (1 / 12) - 1 for p in ipca]


def idx(rets):
    out, v = [100.0], 100.0
    for r in rets:
        v *= 1 + r; out.append(v)
    return out


def mwr_anual(meses, meio=True):
    """TIR dos fluxos mensais (aportes +, retiradas -) com saldo final; fluxo no meio do mês se meio=True."""
    n = len(meses)
    off = 0.5 if meio else 0.0
    alvo = meses[-1]["pat_fim"]
    lo, hi = -0.5, 0.5
    for _ in range(100):
        mid = (lo + hi) / 2
        v = meses[0]["pat_ini"] * (1 + mid) ** n + sum(m["mov"] * (1 + mid) ** (n - k - off) for k, m in enumerate(meses))
        lo, hi = (mid, hi) if v < alvo else (lo, mid)
    i = (lo + hi) / 2
    return i, (1 + i) ** 12 - 1


def janela(a, b):
    r = R[a:b]
    t = comp(r)
    inf = comp(IPCA[a:b])
    out = {"twr": t, "real": (1 + t) / (1 + inf) - 1, "cdi": comp(CDI[a:b]), "ipca": inf}
    for bm in BENCH:
        out[bm["nome"]] = comp(fator_real(bm["spread_real"], IPCA)[a:b])
    return out


JANELAS = [("Mês (" + LAB[-1] + ")", N - 1, N), ("3 meses", N - 3, N), ("6 meses", N - 6, N)]
ano_ini = next((i for i, m in enumerate(M) if m["rotulo"].lower().startswith("jan")), None)
if ano_ini is not None:
    JANELAS.append(("Ano corrente", ano_ini, N))
JANELAS.append((f"Desde o início ({N} meses)", 0, N))
J = {n: janela(a, b) for n, a, b in JANELAS}
TOT = J[JANELAS[-1][0]]
_, MWR = mwr_anual(M, CFG.get("fluxo_meio_do_mes", True))
TWR_ANUAL = (1 + TOT["twr"]) ** (12 / N) - 1

VOL = std(R) * math.sqrt(12)
EXC = [r - c for r, c in zip(R, CDI)]
SHARPE = (mean(EXC) * 12) / VOL if VOL else float("nan")
DOWN = math.sqrt(mean([min(0, e) ** 2 for e in EXC])) * math.sqrt(12)
SORTINO = (mean(EXC) * 12) / DOWN if DOWN else float("nan")
IND = idx(R)
pico, DD, ddser = IND[0], 0.0, []
for v in IND:
    pico = max(pico, v); d = (pico - v) / pico; ddser.append(-d); DD = max(DD, d)
BETA = None
if CFG.get("serie_indice"):
    s = CFG["serie_indice"]; ms, mr = mean(s), mean(R)
    BETA = sum((a - mr) * (b - ms) for a, b in zip(R, s)) / sum((b - ms) ** 2 for b in s)

CAP = {bm["nome"]: capital_mensal(bm["spread_real"], W, ANOS) for bm in BENCH}
CAP_NEC = capital_mensal(R_NEC, W, ANOS)
MES_NEG = sum(1 for r in R if r < 0)
saidas = [(m["rotulo"], -m["mov"]) for m in M if m["mov"] < 0 and m["pat_ini"] > 0]
TOTAL_SAIDAS = sum(v for _, v in saidas)

# ------------------------------------------------------------------ SVG
CHARTS = {}


def esc(v0, v1, a, b): return lambda v: a + (v - v0) * (b - a) / (v1 - v0)


def linhas(cid, xl, series, ymin, ymax, passo, fmt_y, fmt_v, w=760, h=320, ml=56, mr=140, nudge=15):
    mt, mb = 14, 34
    X = esc(0, len(xl) - 1, ml, w - mr)
    Y = esc(ymin, ymax, h - mb, mt)
    o = [f'<svg class="chart" id="{cid}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="{cid}-t">']
    t = ymin
    while t <= ymax + 1e-9:
        o.append(f'<line x1="{ml}" x2="{w - mr}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" class="grid"/><text x="{ml - 8}" y="{Y(t) + 4:.1f}" class="tick" text-anchor="end">{fmt_y(t)}</text>')
        t += passo
    for i, lb in enumerate(xl):
        if i % 2 == 0 or i == len(xl) - 1:
            o.append(f'<text x="{X(i):.1f}" y="{h - 12}" class="tick" text-anchor="middle">{lb}</text>')
    y0 = 0 if ymin < 0 < ymax else ymin
    o.append(f'<line x1="{ml}" x2="{w - mr}" y1="{Y(y0):.1f}" y2="{Y(y0):.1f}" class="axis"/>')
    labs = []
    for s in series:
        d = " ".join(f"{'M' if i == 0 else 'L'}{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(s["v"]))
        dash = f' stroke-dasharray="{s["dash"]}"' if s.get("dash") else ""
        o.append(f'<path d="{d}" fill="none" stroke="var({s["cor"]})" stroke-width="{s.get("sw", 2)}" stroke-linejoin="round"{dash}/>')
        labs.append([Y(s["v"][-1]), s["nome"]])
    labs.sort()
    for k in range(1, len(labs)):
        if labs[k][0] - labs[k - 1][0] < nudge: labs[k][0] = labs[k - 1][0] + nudge
    for yy, n in labs:
        o.append(f'<text x="{w - mr + 6}" y="{yy + 4:.1f}" class="dlabel">{n}</text>')
    o.append(f'<line class="xhair" y1="{mt}" y2="{h - mb}" x1="0" x2="0" visibility="hidden"/><rect class="hit" x="{ml}" y="{mt}" width="{w - ml - mr}" height="{h - mt - mb}" fill="transparent"/></svg>')
    CHARTS[cid] = {"w": w, "xs": [round(X(i), 1) for i in range(len(xl))], "xlabels": xl,
                   "rows": [[f'{s["nome"]}: {fmt_v(s["v"][i])}' for s in series] for i in range(len(xl))]}
    return "\n".join(o)


def barras_v(cid, itens, ymax, fmt, ref=None, ref_lab="", w=760, h=260, cor="--s1"):
    ml, mr, mt, mb = 56, 16, 24, 40
    bw = (w - ml - mr) / len(itens)
    Y = esc(0, ymax, h - mb, mt)
    o = [f'<svg class="chart" id="{cid}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="{cid}-t">']
    passo = ymax / 4
    for k in range(5):
        t = passo * k
        o.append(f'<line x1="{ml}" x2="{w - mr}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" class="grid"/><text x="{ml - 8}" y="{Y(t) + 4:.1f}" class="tick" text-anchor="end">{fmt(t)}</text>')
    for i, (lab, v) in enumerate(itens):
        x = ml + i * bw + 5
        o.append(f'<rect x="{x:.1f}" y="{Y(v):.1f}" width="{bw - 10:.1f}" height="{max(Y(0) - Y(v), 1):.1f}" rx="3" fill="var({cor})"><title>{lab}: {fmt(v)}</title></rect>')
        if v > 0: o.append(f'<text x="{x + (bw - 10) / 2:.1f}" y="{Y(v) - 5:.1f}" class="dlabel" text-anchor="middle">{fmt(v)}</text>')
        o.append(f'<text x="{x + (bw - 10) / 2:.1f}" y="{h - 22}" class="tick" text-anchor="middle">{lab}</text>')
    if ref is not None:
        o.append(f'<line x1="{ml}" x2="{w - mr}" y1="{Y(ref):.1f}" y2="{Y(ref):.1f}" stroke="var(--s2)" stroke-width="2" stroke-dasharray="6 4"/><text x="{ml + 6}" y="{Y(ref) - 6:.1f}" class="dlabel">{ref_lab}</text>')
    o.append(f'<line x1="{ml}" x2="{w - mr}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" class="axis"/></svg>')
    return "\n".join(o)


def barras_h(cid, itens, fmt, w=760, rowh=36, ml=230, mr=90):
    mt = 8
    vmax = max(abs(v) for _, v in itens) or 1
    lo = -vmax if min(v for _, v in itens) < 0 else 0
    X = esc(lo, vmax, ml, w - mr)
    h = mt + rowh * len(itens) + 10
    o = [f'<svg class="chart" id="{cid}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="{cid}-t">']
    for i, (n, v) in enumerate(itens):
        y0 = mt + i * rowh + 4
        x1, x2 = (X(0), X(v)) if v >= 0 else (X(v), X(0))
        o.append(f'<text x="{ml - 10}" y="{y0 + 16}" class="dlabel" text-anchor="end">{n}</text><rect x="{x1:.1f}" y="{y0}" width="{max(x2 - x1, 1.5):.1f}" height="22" rx="3" fill="var(--s1)"><title>{n}: {fmt(v)}</title></rect>')
        o.append(f'<text x="{(x2 + 8) if v >= 0 else (x1 - 8):.1f}" y="{y0 + 16}" class="dlabel" text-anchor="{"start" if v >= 0 else "end"}">{fmt(v)}</text>')
    o.append(f'<line x1="{X(0):.1f}" x2="{X(0):.1f}" y1="{mt}" y2="{h - 6}" class="axis"/></svg>')
    return "\n".join(o)


def tabela(cab, linhas_, cls="num"):
    h = "".join(f"<th>{c}</th>" for c in cab)
    r = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in l) + "</tr>" for l in linhas_)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{r}</tbody></table></div>'


# ------------------------------------------------------------------ corpo
sec = []
tol = PL.get("tolerancia_drawdown")
tol_txt = pct(tol, 1) if tol else "<strong>a combinar com o cliente</strong> (nenhum valor assumido)"
sec.append(f"""<p><span class="pill">Escopo</span> {CFG.get('escopo', '')}</p>
<div class="kpis">
 <div class="kpi"><div class="l">Retorno desde o início ({N} meses)</div><div class="v">{pct(TOT['twr'])}</div><div class="n">{pct(TOT['real'])} acima da inflação · {num(TOT['twr'] / TOT['cdi'] * 100, 0)}% do CDI ({pct(TOT['cdi'])}).</div></div>
 <div class="kpi"><div class="l">Retorno real necessário</div><div class="v">{pct(R_NEC)} a.a.</div><div class="n">para sustentar {brl(W)}/mês até os {ATE} anos com {brl(PV)}. Hoje: {pct(TOT['real'])} real no período.</div></div>
 <div class="kpi"><div class="l">Queda máxima mensal</div><div class="v">{pct(-DD)}</div><div class="n">pior mês: {pct(min(R))}. Meses negativos: {MES_NEG} de {N}.</div></div>
</div>""")

_sit = "acima" if TOT["real"] >= R_NEC else "abaixo"
sec.append(f"""<p>No período, a carteira rendeu {pct(TOT['real'])} acima da inflação, contra {pct(R_NEC)} necessários para o plano: <strong>{_sit} do necessário ({pp(TOT['real'] - R_NEC)})</strong>. Contra o CDI ficou em {num(TOT['twr'] / TOT['cdi'] * 100, 0)}% ({pp(TOT['twr'] - TOT['cdi'])}). Para o plano vale a distância da meta, não a comparação com o CDI.</p>""")
sec.append(f"""<h2>1. Contexto do plano de investimento</h2>
{tabela(["Parâmetro", "Valor"], [
    ["Objetivo", f"Renda de {brl(W)} por mês, em R$ reais, dos {IDADE} aos {ATE} anos ({ANOS} anos)"],
    ["Patrimônio de referência", brl(PV)],
    ["Retorno real necessário (calculado)", f"<strong>{pct(R_NEC)} a.a.</strong> (capital necessário igual ao patrimônio)"],
    *[[f"Capital necessário em {bm['nome']}", brl(CAP[bm['nome']]) + f" (patrimônio {pct(abs(PV / CAP[bm['nome']] - 1), 1)} {'abaixo' if PV < CAP[bm['nome']] else 'acima'})"] for bm in BENCH],
    ["Perda máxima tolerada", tol_txt],
    ["Liquidez", "; ".join(f"{a}: {pct(float(b) / 100 if float(b) > 1 else float(b), 1)}" for a, b, _ in CFG.get("liquidez", [])) or "não informada"],
])}""")

xl = ["início"] + LAB
series = [{"nome": "Carteira", "v": [v - 100 for v in IND], "cor": "--s1", "sw": 2.5},
          {"nome": "CDI", "v": [v - 100 for v in idx(CDI)], "cor": "--mut", "sw": 1.5},
          {"nome": f"Necessário ({pct(R_NEC, 1)} real)", "v": [v - 100 for v in idx(fator_real(R_NEC, IPCA))], "cor": "--s2", "dash": "6 4"}]
for k, bm in enumerate(BENCH):
    if abs(bm["spread_real"] - R_NEC) > 0.002:
        series.append({"nome": bm["nome"], "v": [v - 100 for v in idx(fator_real(bm["spread_real"], IPCA))], "cor": ["--ink2", "--mut"][k % 2], "dash": "2 3", "sw": 1.5})
g1 = linhas("g_traj", xl, series, math.floor(min(min(s["v"]) for s in series)), math.ceil(max(max(s["v"]) for s in series)), 2, lambda t: f"{t:.0f}%", lambda v: num(v) + "%", ml=50)
saidas_chart = barras_v("g_saidas", [(m["rotulo"], max(-m["mov"], 0)) for i, m in enumerate(M) if i >= (ano_ini or 1)], max(max((v for _, v in saidas), default=1) * 1.15, W * 1.2), lambda v: f"{v / 1000:.0f} mil", ref=W, ref_lab=f"Renda desejada: {brl(W)}/mês") if saidas else ""
sec.append(f"""<h2>2. Evolução em relação à meta</h2>
<h3 id="g_traj-t">Retorno acumulado vs. retorno necessário</h3>
<p class="sub">Rentabilidade acumulada desde o início, em %, com o CDI e a linha do retorno real necessário. Cada ponto é o fechamento do mês.</p>
<div class="card wrap" data-chart="g_traj">{g1}<div class="tip"></div></div>
<h3 id="g_saidas-t">Retiradas líquidas por mês vs. renda desejada</h3>
<p class="sub">Saídas líquidas da conta, de {saidas[0][0] if saidas else '—'} em diante. Total de {brl(TOTAL_SAIDAS)} em {len(saidas)} meses com saída.</p>
<div class="card">{saidas_chart}</div>""")

tab_ret = tabela(["Período", "Carteira (TWR)", "Real", "CDI", "Carteira ÷ CDI", *[bm["nome"] for bm in BENCH]],
                 [[n, pct(j["twr"]), pct(j["real"]), pct(j["cdi"]), num(j["twr"] / j["cdi"] * 100, 0) + "%" if j["cdi"] else "—", *[pct(j[bm["nome"]]) for bm in BENCH]] for n, j in J.items()])
tab_risco = tabela(["Indicador", "Valor", "Como ler"], [
    ["Volatilidade anualizada", pct(VOL), f"desvio-padrão dos {N} retornos mensais × √12 (amostra curta)"],
    ["Drawdown máximo (base mensal)", pct(-DD), "do pico ao fundo do índice mensal; não captura quedas dentro do mês"],
    ["Pior mês", pct(min(R)), LAB[R.index(min(R))]],
    ["Índice de Sharpe", num(SHARPE), "excesso sobre o CDI ÷ volatilidade (negativo = rendeu menos que o CDI)"],
    ["Índice de Sortino", num(SORTINO), "só penaliza o excesso negativo sobre o CDI"],
    ["Beta", num(BETA) if BETA is not None else "pendente", "sensibilidade ao índice" if BETA is not None else "falta a série mensal do índice de referência"],
    ["MWR (TIR do cliente, a.a.)", pct(MWR), "considera datas e valores dos aportes e retiradas; fluxos no meio do mês" if CFG.get("fluxo_meio_do_mes", True) else "fluxos no início do mês"],
    ["TWR anualizado", pct(TWR_ANUAL), "avalia a gestão, sem o efeito dos fluxos"],
])
dd_chart = linhas("g_dd", xl, [{"nome": "Drawdown", "v": [d * 100 for d in ddser], "cor": "--s1", "sw": 2}], math.floor(min(ddser) * 100) - 1 if DD > 0.005 else -1, 0, 0.5 if DD < 0.03 else 1, lambda t: f"{t:.1f}%", lambda v: num(v) + "%", h=200, ml=50)
sec.append(f"""<h2>3. Análise técnica</h2>
<h3>3.1 Retorno por período</h3>
<p class="sub">TWR remove o efeito de aportes e resgates e avalia a gestão; o MWR mostra o que o cliente de fato ganhou. A diferença entre os dois vem do momento dos fluxos.</p>
{tab_ret}
<h3>3.2 Risco e retorno ajustado ao risco</h3>
{tab_risco}
<h3 id="g_dd-t">Drawdown mensal</h3>
<div class="card wrap" data-chart="g_dd">{dd_chart}<div class="tip"></div></div>""")

if CFG.get("posicoes"):
    pos = CFG["posicoes"]
    por_classe = {}
    for p in pos:
        por_classe[p["classe"]] = por_classe.get(p["classe"], 0) + p["ganho_acum"]
    enc = CFG.get("encerradas_ganho", 0)
    soma = sum(por_classe.values()) + enc
    itens = sorted(por_classe.items(), key=lambda t: -t[1]) + ([("Posições encerradas no período", enc)] if enc else [])
    g3 = barras_h("g_contrib", itens, lambda v: brl(v))
    linhas_pos = [[p["nome"], p["classe"], brl(p["valor"]), brl(p["ganho_acum"]), pct(p["ganho_acum"] / soma, 1) if soma else "—"] for p in sorted(pos, key=lambda p: -p["ganho_acum"])]
    sec.append(f"""<h3 id="g_contrib-t">3.3 De onde veio o retorno (ganho acumulado em R$ por classe)</h3>
<div class="card">{g3}</div>
{tabela(["Posição atual", "Classe", "Valor", "Ganho acumulado", "% do ganho total"], linhas_pos)}
<p>Ganho total no período: {brl(soma)}. A decomposição entre alocação e seleção exige o benchmark por classe e fica pendente.</p>""")

if CFG.get("limites"):
    L = CFG["limites"]
    lin = []
    for c, atual, mn, mx in L["classes"]:
        st = "dentro" if (mn or 0) - 1e-9 <= atual <= mx + 1e-9 else (f"acima do máximo ({pp(atual - mx)})" if atual > mx else f"abaixo do mínimo ({pp(atual - mn)})")
        lin.append([c, pct(atual), f"{pct(mn or 0, 1)} a {pct(mx, 1)}", st])
    alertas = "".join(f"<li>{a}</li>" for a in L.get("alertas", []))
    sec.append(f"""<h3>3.4 Carteira contra as regras da Portfel</h3>
<p class="sub">{L.get('fonte', '')}</p>
{tabela(["Classe", "Hoje", "Faixa do perfil", "Situação"], lin)}
<ul>{alertas}</ul>""")

for ex in CFG.get("extras", []):
    sec.append(f"<h3>{ex['titulo']}</h3>" + (f"<p class=\"sub\">{ex['texto']}</p>" if ex.get("texto") else "") + tabela(ex["tabela"]["cab"], ex["tabela"]["linhas"]))

if CFG.get("pendencias"):
    sec.append("<h2>Pendências e decisões em aberto</h2><ul>" + "".join(f"<li>{p}</li>" for p in CFG["pendencias"]) + "</ul>")
if CFG.get("fontes"):
    sec.append("<h2>Fontes dos dados e premissas</h2>" + tabela(["Dado ou premissa", "Valor", "Origem"], CFG["fontes"], ""))
sec.append("""<h2>Metodologia</h2><ul>
 <li>TWR: produto dos retornos mensais informados pelo custodiante. MWR: TIR dos fluxos mensais. Real: deflacionado pelo IPCA do mês.</li>
 <li>Volatilidade, Sharpe e Sortino com poucos pontos mensais são indicativos. Drawdown em base mensal não mostra quedas dentro do mês.</li>
 <li>Retorno necessário: taxa real que torna o capital necessário (retirada no início do mês) igual ao patrimônio de referência.</li>
 <li>A perda máxima tolerada é combinada com o cliente: o relatório mostra o drawdown como resultado e não define limite.</li>
 <li>Rentabilidade passada não garante rentabilidade futura. Conteúdo para revisão do consultor.</li></ul>""")

base = (Path(__file__).resolve().parent.parent / "assets" / "relatorio_base.html").read_text(encoding="utf-8")
out = (base.replace("%%TITULO_PAGINA%%", CFG.get("titulo_pagina", "Relatório de Performance")).replace("%%H1%%", CFG.get("titulo", "Relatório de performance"))
       .replace("%%SUB%%", CFG.get("subtitulo", "")).replace("%%AVISO%%", CFG.get("aviso", "<strong>Dados reais.</strong> Conteúdo para revisão do consultor antes de qualquer envio ao cliente."))
       .replace("%%RODAPE%%", f"Data-base {CFG.get('data_base', '')} · gerado por relatorio_performance_real.py").replace("%%CORPO%%", "\n".join(sec))
       .replace("%%CHARTS_JSON%%", json.dumps(CHARTS, ensure_ascii=False)))
SAIDA.write_text(out, encoding="utf-8")
print("escrito:", SAIDA)
print(f"TWR {pct(TOT['twr'])} | real {pct(TOT['real'])} | CDI {pct(TOT['cdi'])} | MWR a.a. {pct(MWR)} | vol {pct(VOL)} | DD {pct(-DD)} | Sharpe {num(SHARPE)} | Sortino {num(SORTINO)} | r_nec {pct(R_NEC)}")
