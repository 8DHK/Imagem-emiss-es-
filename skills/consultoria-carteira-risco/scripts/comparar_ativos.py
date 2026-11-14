#!/usr/bin/env python3
"""Compara DIVO11 e BRAX11: qual aumenta mais o risco (volatilidade e drawdown) da carteira?
Dados: fechamentos diários (stockanalysis.com) e CDI diário (BCB/SGS 12), 31/ago a 11/nov/2026.
Janela curta (49 retornos): leitura preliminar, não conclusão definitiva."""
import math

# fechamentos do mais antigo (31/ago) ao mais recente (11/nov)
DIVO = [127.19,128.74,132.62,132.50,132.85,134.78,132.22,134.43,133.95,132.86,132.95,133.21,132.43,132.16,132.96,133.39,131.89,130.79,130.20,129.98,130.35,132.78,132.90,136.00,145.29,146.00,145.24,146.10,148.05,146.00,146.30,144.30,145.28,144.44,146.13,146.55,145.08,146.12,126.57,126.15,122.42,120.68,119.74,118.30,119.21,118.30,119.92,123.20,122.60,123.64]
BRAX = [149.26,150.91,155.45,155.31,155.27,157.11,155.14,157.95,157.04,154.80,156.44,155.44,155.82,155.21,155.91,156.46,155.64,153.30,153.60,153.25,153.87,155.97,156.73,160.84,172.64,172.17,171.00,172.39,175.25,173.36,173.08,170.89,172.02,171.87,174.50,172.66,171.01,171.90,148.32,147.29,143.37,141.83,140.90,138.84,140.07,139.18,141.06,144.07,143.34,143.96]
CDI_D = [0.05166]*13 + [0.050788]*(50-13)   # % a.d. (taxa muda em 17/set)
assert len(DIVO) == len(BRAX) == 50

def ret(p): return [p[i]/p[i-1]-1 for i in range(1, len(p))]
rd, rb = ret(DIVO), ret(BRAX)
cdi = [c/100 for c in CDI_D[1:]]                   # CDI de cada dia útil dos 49 retornos
mean = lambda x: sum(x)/len(x)
def std(x): m=mean(x); return math.sqrt(sum((v-m)**2 for v in x)/(len(x)-1))
def corr(a,b):
    ma,mb=mean(a),mean(b); return sum((x-ma)*(y-mb) for x,y in zip(a,b))/math.sqrt(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))
def beta(a,b):
    ma,mb=mean(a),mean(b); return sum((x-ma)*(y-mb) for x,y in zip(a,b))/sum((y-mb)**2 for y in b)
def maxdd(r):
    v=pk=1.0; dd=0
    for x in r:
        v*=1+x; pk=max(pk,v); dd=max(dd,(pk-v)/pk)
    return dd
def vol(r): return std(r)*math.sqrt(252)

print("== Isolados (49 pregões) ==")
for n,r in (("DIVO11",rd),("BRAX11",rb)):
    print(f"{n}: vol anual {vol(r):.1%} | drawdown máx {maxdd(r):.1%} | pior dia {min(r):.1%} | retorno {math.prod(1+x for x in r)-1:+.1%}")
print(f"correlação diária DIVO11×BRAX11: {corr(rd,rb):.2f} | beta DIVO11 vs BRAX11: {beta(rd,rb):.2f}")
sem = lambda r: [x for i,x in enumerate(r) if i != 37]      # sem o dia 26/out (índice 37)
print(f"sem 26/out: vol DIVO11 {vol(sem(rd)):.1%} | BRAX11 {vol(sem(rb)):.1%} | dd DIVO11 {maxdd(sem(rd)):.1%} | BRAX11 {maxdd(sem(rb)):.1%}")

print("\n== Carteira do exemplo: 70% CDI (RF + multimercado) + 30% ETF ==")
def cart(wetf, ret_etf): return [(1-wetf)*c + wetf*e for c,e in zip(cdi,ret_etf)]
for n,r in (("30% DIVO11",rd),("30% BRAX11",rb)):
    c=cart(0.30,r); print(f"{n}: vol {vol(c):.1%} | drawdown máx {maxdd(c):.1%} | pior dia {min(c):.1%}")
c_base=cart(0.0,rd); print(f"só CDI: vol {vol(c_base):.2%}")
mix=[(1-0.30)*c+0.15*a+0.15*b for c,a,b in zip(cdi,rd,rb)]
print(f"15% DIVO11 + 15% BRAX11: vol {vol(mix):.1%} | drawdown máx {maxdd(mix):.1%}")

print("\n== Quanto de cada ETF cabe no limite de drawdown de 8% (nesta janela) ==")
for n,r in (("DIVO11",rd),("BRAX11",rb)):
    lo,hi=0.0,1.0
    for _ in range(40):
        m=(lo+hi)/2; lo,hi=(m,hi) if maxdd(cart(m,r))<=0.08 else (lo,m)
    print(f"{n}: peso máximo ≈ {lo:.0%}")

print("\n== Contribuição marginal ao risco (carteira 70% CDI + 30% DIVO11, adicionando BRAX11) ==")
base=cart(0.30,rd)
for n,r in (("DIVO11",rd),("BRAX11",rb)):
    print(f"beta de {n} em relação à carteira-base: {beta(r,base):.2f}")
