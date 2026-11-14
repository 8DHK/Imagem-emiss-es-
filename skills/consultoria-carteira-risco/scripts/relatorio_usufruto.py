#!/usr/bin/env python3
"""Gera o HTML "Estudo de usufruto" (gráficos e simulações) a partir de um JSON de configuração.

Uso:  python3 relatorio_usufruto.py config.json saida.html
Os dados do cliente ficam SÓ no config.json (nunca no repositório). Exemplo de config em ../assets/exemplo_config_usufruto.json
Campos: subtitulo, idade, patrimonio, retirada_mensal, horizontes [80, 90], cenarios [{nome, mu, sigma, cor?}], cenario_base,
        serie_real [[rotulo, R$ mi]], retornos_recentes [[rotulo, "+0,93%"]], choque {data, itens [[nome, pp]], total_pp, nota},
        alocacao [{classe, atual, min, max}], pontos_de_atencao [texto],
        fontes [[dado, valor, origem]]
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analise_usufruto as au  # noqa: E402

CFG = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
SAIDA = Path(sys.argv[2])


def pct(x, d=1): return f"{x * 100:.{d}f}%".replace(".", ",")
def brl(x): return "R$ " + f"{x:,.0f}".replace(",", ".")
def mi(x, d=2): return "R$ " + f"{x / 1e6:.{d}f}".replace(".", ",") + " mi"
def num(x, d=2): return f"{x:.{d}f}".replace(".", ",")
def pp(x, d=2): return f"{x:+.{d}f}".replace(".", ",") + " p.p."


PV, W, IDADE = CFG["patrimonio"], CFG["retirada_mensal"], CFG["idade"]
HOR = CFG.get("horizontes", [80, 90])
CEN = CFG["cenarios"]
BASE = CFG.get("cenario_base", len(CEN) - 1)
CORES = ["--s2", "--mut", "--s1", "--ink2"]
ANOS = max(HOR) - IDADE
N = 10_000
Z = np.random.default_rng(2026).standard_normal((N, ANOS * 12))
TAXA = 12 * W / PV
NFMT = f"{N:,}".replace(",", ".")
CHARTS = {}

# ------------------------------------------------------------------ simulações
for i, c in enumerate(CEN):
    c["cor"] = c.get("cor", CORES[i % len(CORES)])
    c["paths"] = au.mc_paths(PV, W, c["mu"], c["sigma"], ANOS, N, z=Z)
    ann = c["paths"][:, ::12]
    c["fan"] = {q: np.percentile(ann, q, axis=0) for q in (5, 25, 50, 75, 95)}
    c["esgotado"] = (ann <= 0).mean(axis=0)
    c["p"] = {h: float((c["paths"][:, (h - IDADE) * 12] > 0).mean()) for h in HOR}
    c["pat"] = {h: {q: float(np.percentile(c["paths"][:, (h - IDADE) * 12], q)) for q in (10, 50, 90)} for h in HOR}
    c["ret90"] = {h: au.retirada_para_prob(PV, c["mu"], c["sigma"], h - IDADE, 0.9, n=4000) for h in HOR}
    c["det"] = au.plano_anual(PV, W, c["mu"], 95 - IDADE)
    c["zera"] = au.anos_ate_zerar(PV, W, c["mu"])
    c["ret_det"] = {h: au.retirada_sustentavel(PV, c["mu"], h - IDADE) for h in HOR}
b = CEN[BASE]
freq = [(n, au.mc_sucesso(PV, W, b["mu"], b["sigma"], HOR[0] - IDADE, 6000, z=Z, freq_meses=f)[0])
        for n, f in (("Mensal", 1), ("Semestral, no início do semestre", 6), ("Anual, no início do ano", 12))]


# ------------------------------------------------------------------ SVG
def esc(v0, v1, a, b_): return lambda v: a + (v - v0) * (b_ - a) / (v1 - v0)


def eixo_x(o, X, h, mb, idades):
    for a in idades:
        o.append(f'<text x="{X(a):.1f}" y="{h - 12}" class="tick" text-anchor="middle">{a}</text>')


def fan(cid, c):
    w, h, ml, mr, mt, mb = 760, 330, 56, 118, 14, 34
    X = esc(IDADE, IDADE + ANOS, ml, w - mr)
    ymax = max(math.ceil(c["fan"][95].max() / 5e5) * 5e5, math.ceil(PV * 1.1 / 5e5) * 5e5) / 1e6
    Y = esc(0, ymax, h - mb, mt)
    o = [f'<svg class="chart" id="{cid}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="{cid}-t">']
    t = 0.0
    while t <= ymax + 1e-9:
        o.append(f'<line x1="{ml}" x2="{w - mr}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" class="grid"/>')
        o.append(f'<text x="{ml - 8}" y="{Y(t) + 4:.1f}" class="tick" text-anchor="end">{num(t, 1)}</text>')
        t += 0.5 if ymax <= 4 else 1
    eixo_x(o, X, h, mb, range(IDADE, IDADE + ANOS + 1, 5))
    o.append(f'<line x1="{ml}" x2="{w - mr}" y1="{Y(0)}" y2="{Y(0)}" class="axis"/>')
    ages = list(range(IDADE, IDADE + ANOS + 1))

    def poly(lo, hi, k):
        pts = [f"{X(a):.1f},{Y(hi[i] / 1e6):.1f}" for i, a in enumerate(ages)] + [f"{X(a):.1f},{Y(lo[i] / 1e6):.1f}" for i, a in reversed(list(enumerate(ages)))]
        o.append(f'<polygon points="{" ".join(pts)}" class="{k}"/>')
    poly(c["fan"][5], c["fan"][95], "band"); poly(c["fan"][25], c["fan"][75], "band2")
    path = lambda v: " ".join(f"{'M' if i == 0 else 'L'}{X(a):.1f},{Y(v[i] / 1e6):.1f}" for i, a in enumerate(ages))
    o.append(f'<path d="{path(c["fan"][50])}" fill="none" stroke="var(--s1)" stroke-width="2.5" stroke-linejoin="round"/>')
    det = np.array(c["det"][:ANOS + 1]).clip(0)
    o.append(f'<path d="{path(det)}" fill="none" stroke="var(--ink2)" stroke-width="1.5" stroke-dasharray="5 4"/>')
    for hz in HOR:
        o.append(f'<line x1="{X(hz):.1f}" x2="{X(hz):.1f}" y1="{mt}" y2="{h - mb}" stroke="var(--axis)" stroke-dasharray="2 3"/>')
        o.append(f'<text x="{X(hz) - 4:.1f}" y="{mt + 10}" class="dlabel" text-anchor="end" style="fill:var(--ink2)">{hz} anos</text>')
    rot = [(c["fan"][95][-1], "P95"), (c["fan"][50][-1], "Mediana"), (det[-1], "Retorno constante"), (c["fan"][5][-1], "P5")]
    ys = []
    for v, n in sorted(rot, key=lambda t_: Y(t_[0] / 1e6)):
        yy = Y(v / 1e6)
        if ys and yy - ys[-1] < 15: yy = ys[-1] + 15
        ys.append(yy)
        o.append(f'<text x="{w - mr + 6}" y="{yy + 4:.1f}" class="dlabel">{n}</text>')
    o.append('<line class="xhair" y1="%d" y2="%d" x1="0" x2="0" visibility="hidden"/>' % (mt, h - mb))
    o.append(f'<rect class="hit" x="{ml}" y="{mt}" width="{w - ml - mr}" height="{h - mt - mb}" fill="transparent"/></svg>')
    CHARTS[cid] = {"w": w, "xs": [round(X(a), 1) for a in ages], "xlabels": [f"{a} anos" for a in ages],
                   "rows": [[f"P95: {mi(c['fan'][95][i])}", f"P75: {mi(c['fan'][75][i])}", f"Mediana: {mi(c['fan'][50][i])}",
                             f"P25: {mi(c['fan'][25][i])}", f"P5: {mi(c['fan'][5][i])}",
                             f"Retorno constante: {mi(max(c['det'][i], 0))}", f"Já sem patrimônio: {pct(c['esgotado'][i], 0)}"] for i in range(len(ages))]}
    return "\n".join(o)


def det_chart():
    w, h, ml, mr, mt, mb = 760, 300, 56, 150, 14, 34
    fim = 95
    X = esc(IDADE, fim, ml, w - mr)
    ymax = math.ceil(PV * 1.1 / 5e5) * 5e5 / 1e6
    Y = esc(0, ymax, h - mb, mt)
    o = [f'<svg class="chart" id="g_det" viewBox="0 0 {w} {h}" role="img" aria-labelledby="g_det-t">']
    t = 0.0
    while t <= ymax + 1e-9:
        o.append(f'<line x1="{ml}" x2="{w - mr}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" class="grid"/>')
        o.append(f'<text x="{ml - 8}" y="{Y(t) + 4:.1f}" class="tick" text-anchor="end">{num(t, 1)}</text>')
        t += 0.5
    eixo_x(o, X, h, mb, range(IDADE, fim + 1, 5))
    o.append(f'<line x1="{ml}" x2="{w - mr}" y1="{Y(0)}" y2="{Y(0)}" class="axis"/>')
    ages = list(range(IDADE, fim + 1))
    labs = []
    for c in CEN:
        v = np.array(c["det"][:len(ages)]).clip(0) / 1e6
        d = " ".join(f"{'M' if i == 0 else 'L'}{X(a):.1f},{Y(v[i]):.1f}" for i, a in enumerate(ages))
        sw = 2.5 if c is b else 1.8
        o.append(f'<path d="{d}" fill="none" stroke="var({c["cor"]})" stroke-width="{sw}" stroke-linejoin="round"/>')
        labs.append([Y(v[-1]), f'{c["nome"]}'])
    labs.sort()
    for k in range(1, len(labs)):
        if labs[k][0] - labs[k - 1][0] < 15: labs[k][0] = labs[k - 1][0] + 15
    for yy, n in labs:
        o.append(f'<text x="{w - mr + 6}" y="{yy + 4:.1f}" class="dlabel">{n}</text>')
    o.append('<line class="xhair" y1="%d" y2="%d" x1="0" x2="0" visibility="hidden"/>' % (mt, h - mb))
    o.append(f'<rect class="hit" x="{ml}" y="{mt}" width="{w - ml - mr}" height="{h - mt - mb}" fill="transparent"/></svg>')
    CHARTS["g_det"] = {"w": w, "xs": [round(X(a), 1) for a in ages], "xlabels": [f"{a} anos" for a in ages],
                       "rows": [[f"{c['nome']}: {mi(max(c['det'][i], 0))}" for c in CEN] for i in range(len(ages))]}
    return "\n".join(o)


def barras_v(cid, itens, ymax, titulo_y):
    w, h, ml, mr, mt, mb = 760, 250, 50, 16, 24, 40
    bw = (w - ml - mr) / len(itens)
    Y = esc(0, ymax, h - mb, mt)
    o = [f'<svg class="chart" id="{cid}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="{cid}-t">']
    t = 0.0
    while t <= ymax + 1e-9:
        o.append(f'<line x1="{ml}" x2="{w - mr}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" class="grid"/>')
        o.append(f'<text x="{ml - 8}" y="{Y(t) + 4:.1f}" class="tick" text-anchor="end">{num(t, 1)}</text>')
        t += 0.5
    for i, (lab, v, em) in enumerate(itens):
        x = ml + i * bw + 5
        o.append(f'<rect x="{x:.1f}" y="{Y(v):.1f}" width="{bw - 10:.1f}" height="{max(Y(0) - Y(v), 1):.1f}" rx="3" fill="{"var(--s2)" if em else "var(--s1)"}"><title>{lab}: R$ {num(v)} mi</title></rect>')
        o.append(f'<text x="{x + (bw - 10) / 2:.1f}" y="{Y(v) - 5:.1f}" class="dlabel" text-anchor="middle">{num(v)}</text>')
        o.append(f'<text x="{x + (bw - 10) / 2:.1f}" y="{h - 22}" class="tick" text-anchor="middle">{lab}</text>')
    o.append(f'<text x="{ml}" y="{mt - 8}" class="tick">{titulo_y}</text>')
    o.append(f'<line x1="{ml}" x2="{w - mr}" y1="{Y(0)}" y2="{Y(0)}" class="axis"/></svg>')
    return "\n".join(o)


def prob_chart():
    w, ml, mr, mt, rowh = 760, 170, 60, 8, 30
    h = mt + (len(CEN) * (len(HOR) * 24 + 14)) + 28
    X = esc(0, 1, ml, w - mr)
    cores = ["var(--s1)", "var(--s2)", "var(--mut)"]
    o = [f'<svg class="chart" id="g_prob" viewBox="0 0 {w} {h}" role="img" aria-labelledby="g_prob-t">']
    for t in range(0, 101, 20):
        o.append(f'<line x1="{X(t / 100):.1f}" x2="{X(t / 100):.1f}" y1="{mt}" y2="{h - 22}" class="grid"/>')
        o.append(f'<text x="{X(t / 100):.1f}" y="{h - 6}" class="tick" text-anchor="middle">{t}%</text>')
    y = mt
    for c in CEN:
        o.append(f'<text x="{ml - 10}" y="{y + 12 + (len(HOR) * 24) / 2 - 6:.1f}" class="dlabel" text-anchor="end">{c["nome"]}</text>')
        for k, hz in enumerate(HOR):
            v = c["p"][hz]
            o.append(f'<rect x="{ml}" y="{y + k * 24}" width="{max(X(v) - ml, 1.5):.1f}" height="18" rx="3" fill="{cores[k]}"><title>{c["nome"]}, até {hz} anos: {pct(v)}</title></rect>')
            o.append(f'<text x="{X(v) + 6:.1f}" y="{y + k * 24 + 13}" class="dlabel">{pct(v, 0)}</text>')
        y += len(HOR) * 24 + 14
    o.append(f'<line x1="{ml}" x2="{ml}" y1="{mt}" y2="{h - 22}" class="axis"/></svg>')
    leg = "".join(f'<span><i style="background:{cores[k]}"></i>Dura até {hz} anos</span>' for k, hz in enumerate(HOR))
    return "\n".join(o) + f'<div class="leg">{leg}</div>'


def choque_chart(ch):
    itens = ch["itens"]
    w, rowh, ml, mr, mt = 760, 40, 190, 80, 8
    h = mt + rowh * len(itens) + 30
    lo = math.floor(min(v for _, v in itens) * 2) / 2
    X = esc(lo, 0, ml, w - mr)
    o = [f'<svg class="chart" id="g_choque" viewBox="0 0 {w} {h}" role="img" aria-labelledby="g_choque-t">']
    t = lo
    while t <= 1e-9:
        o.append(f'<line x1="{X(t):.1f}" x2="{X(t):.1f}" y1="{mt}" y2="{h - 22}" class="grid"/>')
        o.append(f'<text x="{X(t):.1f}" y="{h - 6}" class="tick" text-anchor="middle">{num(t, 1)} p.p.</text>')
        t += 0.5
    for i, (n_, v) in enumerate(itens):
        y0 = mt + i * rowh + 8
        o.append(f'<text x="{ml - 10}" y="{y0 + 16}" class="dlabel" text-anchor="end">{n_}</text>')
        o.append(f'<rect x="{X(v):.1f}" y="{y0}" width="{max(X(0) - X(v), 1.5):.1f}" height="22" rx="3" fill="var(--s1)"><title>{n_}: {pp(v, 3)}</title></rect>')
        o.append(f'<text x="{X(v) - 8:.1f}" y="{y0 + 16}" class="dlabel" text-anchor="end">{num(v, 2)}</text>')
    o.append(f'<line x1="{X(0):.1f}" x2="{X(0):.1f}" y1="{mt}" y2="{h - 22}" class="axis"/></svg>')
    return "\n".join(o)


def tabela(cab, linhas, cls="num"):
    h = "".join(f"<th>{c}</th>" for c in cab)
    r = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in l) + "</tr>" for l in linhas)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{r}</tbody></table></div>'


# ------------------------------------------------------------------ blocos
sec = []
sec.append(f"""<div class="kpis">
 <div class="kpi"><div class="l">Retirada sobre o patrimônio</div><div class="v">{pct(TAXA)} ao ano</div><div class="n">{brl(W)}/mês sobre {brl(PV)}. Para 50+ anos, taxas de 4% a 5% são o usual.</div></div>
 <div class="kpi"><div class="l">Dura até {HOR[0]} / {HOR[1]} anos ({b['nome']})</div><div class="v">{pct(b['p'][HOR[0]], 0)} / {pct(b['p'][HOR[1]], 0)}</div><div class="n">{NFMT} trajetórias, retorno real médio de {pct(b['mu'], 0)} e volatilidade de {pct(b['sigma'], 0)}.</div></div>
 <div class="kpi"><div class="l">Retirada com 90% de chance</div><div class="v">{brl(b['ret90'][HOR[0]])}</div><div class="n">por mês até os {HOR[0]} anos ({brl(b['ret90'][HOR[1]])} até os {HOR[1]}), no cenário {b['nome']}.</div></div>
</div>""")

if CFG.get("serie_real"):
    s = CFG["serie_real"]
    ymax = math.ceil(max(v for _, v in s) * 2 + 0.5) / 2
    sec.append(f"""<h2>1. Patrimônio nos últimos 12 meses</h2>
<p class="sub">Valores do relatório de performance (R$ milhões). O dado mostra o patrimônio, não o retorno: sem as retiradas e aportes do período, não dá para separar uma coisa da outra.</p>
<div class="card">{barras_v("g_serie", [(r, v, i == len(s) - 1) for i, (r, v) in enumerate(s)], ymax, "R$ milhões")}</div>
{tabela(["Período", "Variação"], CFG.get("retornos_recentes", [])) if CFG.get("retornos_recentes") else ""}""")

sec.append(f"""<h2>2. O plano com retorno constante</h2>
<p class="sub">Retorno real fixo e retirada no fim do ano, a convenção do plano. Cada linha é um retorno real ao ano. Não tem risco nem sequência de retornos.</p>
<div class="card wrap" data-chart="g_det"><h3 id="g_det-t" style="margin-top:0">Patrimônio real (R$ milhões) por idade</h3>{det_chart()}<div class="tip"></div></div>
{tabela(["Cenário", "O patrimônio acaba", *[f"Retirada sustentável até {h} anos" for h in HOR]], [[c["nome"], "nunca" if math.isinf(c["zera"]) else f'aos {IDADE + c["zera"]:.0f} anos', *[brl(c["ret_det"][h]) + "/mês" for h in HOR]] for c in CEN])}""")

botoes = "".join(f'<button type="button" class="segb{" on" if i == BASE else ""}" data-s="{i}">{c["nome"]}</button>' for i, c in enumerate(CEN))
fans = "".join(f'<div class="card wrap scen" data-s="{i}" data-chart="g_fan{i}"{"" if i == BASE else " hidden"}>{fan(f"g_fan{i}", c)}<div class="tip"></div></div>' for i, c in enumerate(CEN))
sec.append(f"""<h2>3. Simulações de Monte Carlo</h2>
<p class="sub">Retornos reais aleatórios (volatilidade anual na premissa de cada cenário), retiradas mensais constantes de {brl(W)}. Faixas: P25–P75 (escura) e P5–P95 (clara), em R$ milhões por idade. A linha tracejada é o retorno constante.</p>
<div class="seg" role="group" aria-label="Cenário">{botoes}</div>
<h3 id="g_fan0-t">Evolução do patrimônio</h3>
{fans}
<div class="leg"><span><i style="background:var(--band2)"></i>P25–P75</span><span><i style="background:var(--band)"></i>P5–P95</span></div>
<h3 id="g_prob-t">Chance de o dinheiro durar</h3>
<div class="card">{prob_chart()}</div>
{tabela(["Cenário", *[f"Dura até {h}" for h in HOR], *[f"Patrimônio aos {h}: P10 / mediana / P90" for h in HOR]], [[c["nome"], *[pct(c["p"][h], 0) for h in HOR], *[f'{mi(c["pat"][h][10], 1)} / {mi(c["pat"][h][50], 1)} / {mi(c["pat"][h][90], 1)}' for h in HOR]] for c in CEN])}
<p>Com retorno igual ao assumido, o plano termina perto de zero. Qualquer sequência pior que a média esgota o patrimônio, e isso explica as probabilidades acima de 0% e abaixo de 100% mesmo no cenário do plano.</p>""")

sec.append(f"""<h2>4. Quanto retirar com 90% de chance</h2>
{tabela(["Cenário", *[f"Até {h} anos" for h in HOR], "Diferença para a retirada atual"], [[c["nome"], *[brl(c["ret90"][h]) + "/mês" for h in HOR], f'{(c["ret90"][HOR[0]] / W - 1) * 100:+.0f}% (até {HOR[0]})'.replace(".", ",")] for c in CEN])}
<h3>Frequência da retirada ({b['nome']}, até {HOR[0]} anos)</h3>
<p class="sub">O mesmo valor total por ano, tirado de uma vez no início do período, rende menos.</p>
{tabela(["Como retira", "Chance de durar"], [[n_, pct(p_, 0)] for n_, p_ in freq])}""")

if CFG.get("choque"):
    ch = CFG["choque"]
    sec.append(f"""<h2>5. De onde vem a oscilação: dia {ch['data']}</h2>
<p class="sub">Contribuição de cada posição listada para o retorno do patrimônio no dia de maior queda (peso × retorno do dia, em pontos percentuais). {ch.get('nota', '')}</p>
<div class="card" id="g_choque-t">{choque_chart(ch)}</div>
<p>O conjunto das posições listadas perdeu {num(abs(ch['total_pp']))}% do patrimônio no dia. O ETF de ações, com peso pequeno, pesou tanto quanto o prefixado, que é bem maior na carteira.</p>""")

if CFG.get("alocacao"):
    linhas = []
    for a in CFG["alocacao"]:
        st = "dentro" if a["min"] - 1e-9 <= a["atual"] <= a["max"] + 1e-9 else (f'acima do máximo ({pp((a["atual"] - a["max"]) * 100)})' if a["atual"] > a["max"] else f'abaixo do mínimo ({pp((a["atual"] - a["min"]) * 100)})')
        linhas.append([a["classe"], pct(a["atual"], 2), f'{pct(a["min"], 1)} a {pct(a["max"], 1)}', st])
    atencao = "".join(f"<li>{t}</li>" for t in CFG.get("pontos_de_atencao", []))
    sec.append(f"""<h2>6. Carteira e regras do perfil</h2>
{tabela(["Classe", "Hoje", "Faixa do perfil", "Situação"], linhas)}
<ul>{atencao}</ul>""")

if CFG.get("fontes"):
    sec.append("<h2>Fontes dos dados e premissas</h2><p class=\"sub\">Origem de cada número. Premissas do analista aparecem marcadas.</p>"
               + tabela(["Dado ou premissa", "Valor", "Origem"], CFG["fontes"], ""))

sec.append(f"""<h2>Metodologia e limites</h2>
<ul>
 <li>Valores em R$ reais (poder de compra de hoje); retornos reais, brutos de imposto e taxas. Imposto e taxa reduzem o retorno líquido.</li>
 <li>Retornos mensais log-normais e independentes, com média e volatilidade anuais iguais às do cenário. A volatilidade é uma premissa do analista, não uma medição da carteira.</li>
 <li>Retiradas constantes em termos reais, no início do mês (no gráfico de retorno constante, no fim do ano, como no plano). Não há aportes.</li>
 <li>A simulação trata a carteira por retorno e volatilidade médios. Ela não supõe travar taxa: ETFs de duração constante e títulos levados ao vencimento têm a mesma taxa de partida e diferem na previsibilidade e na marcação a mercado.</li>
 <li>Vale só para os ativos informados. Outros patrimônios, renda de outras fontes, imposto de renda, sucessão e inflação inesperada não entram.</li>
 <li>Rentabilidade passada não garante rentabilidade futura. Conteúdo para revisão do consultor antes de qualquer envio ao cliente.</li>
</ul>""")

CSS_JS = (Path(__file__).resolve().parent.parent / "assets" / "usufruto_base.html").read_text(encoding="utf-8")
out = (CSS_JS.replace("%%SUB%%", CFG.get("subtitulo", "")).replace("%%CORPO%%", "\n".join(sec))
       .replace("%%CHARTS_JSON%%", json.dumps(CHARTS, ensure_ascii=False)))
SAIDA.write_text(out, encoding="utf-8")
print("escrito:", SAIDA)
print(f"retirada {pct(TAXA)} a.a. | base '{b['nome']}': dura até {HOR[0]} {pct(b['p'][HOR[0]], 0)}, até {HOR[1]} {pct(b['p'][HOR[1]], 0)} | retirada 90%: {brl(b['ret90'][HOR[0]])} / {brl(b['ret90'][HOR[1]])}")
