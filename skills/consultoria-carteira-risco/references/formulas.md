# Fórmulas e API

## Retorno
- Simples: R = Vf / Vi − 1.
- **TWR** (avalia a gestão, tira o efeito de aportes e resgates): ∏(1 + Rᵢ) − 1 sobre subperíodos entre fluxos.
- **MWR** (o que o cliente de fato ganhou): TIR dos fluxos. Aportes no início do mês: Vfinal = Σ Fₜ·(1+i)^(T−t), resolver i e anualizar.
- Real: (1 + nominal) / (1 + IPCA) − 1.
- Anualizar: (1 + R)^(12/meses) − 1.
- A diferença entre TWR e MWR é informação (timing dos aportes).

## Meta
- Valor futuro com aportes ao fim do mês: FV = PV·(1+r)^n + PMT·((1+i)^n − 1)/i, com i = (1+r_ano)^(1/12) − 1.
- **Retorno necessário:** resolver r tal que FV = meta (bisseção). Exemplo do texto-fonte (R$ 200 mil + R$ 1.500/mês, R$ 1 mi em 15 anos): **6,84% a.a. real**, não 4,5%.
- Aporte necessário para um retorno dado: PMT = (meta − PV·(1+i)^n)·i / ((1+i)^n − 1).

## Risco
- Volatilidade anualizada: σ_mensal × √12 (diária: × √252).
- Drawdown: (pico − fundo) / pico sobre o índice acumulado; reportar também o tempo de recuperação.
- Sharpe: média do excesso sobre o CDI × 12 ÷ volatilidade. Sortino: mesmo numerador, ÷ desvio só dos excessos negativos. Beta: cov(carteira, índice) / var(índice).
- Volatilidade da carteira: √(wᵀΣw), com Σ = diag(σ)·Corr·diag(σ).

## Atribuição (Brinson-Fachler por classe)
- Alocação = (w_p − w_b)·(R_b,i − R_b,total); Seleção = w_b·(R_p,i − R_b,i); Interação = (w_p − w_b)·(R_p,i − R_b,i).
- Contribuição = w_p·R_p,i. A diferença para o retorno composto da carteira é efeito de rebalanceamento mensal (mostrar como resíduo).

## Monte Carlo (`scripts/monte_carlo.py`)
- Retornos mensais log-normais calibrados para que média e volatilidade **anuais** (aritméticas) batam: s_ln = √ln(1+(σ/(1+μ))²), m_ln = ln(1+μ) − s_ln²/2; mensal = m_ln/12 e s_ln/√12. Choques correlacionados por **Cholesky** da matriz de correlação.
- Aporte mensal compra pela alocação-alvo. Rebalanceamento: `"anual"`, `"banda"` (parâmetro `banda=0.05`) ou `"nenhum"`.
- Funções: `normais(n, h, seed, k)`, `t_student(..., df=5, k)` (caudas pesadas), `sim(w, pmt, Z, mu, sig, corr, rebal, banda, choque, horizonte, v0)` → `(T, I, n_rebal)`; `resumo(T, I, meta)`; `aporte_para_prob(prob, w, Z)`; `det(w, pmt)` (cenário linear); `port_stats(w, mu, sig, corr)`.
- `choque={ano: retorno_ações}` impõe retorno determinístico no ativo 0 (ações) naquele ano, para testar risco de sequência.
- 10.000 trajetórias × 360 meses leva ~0,5 s por simulação; a busca de aporte (30 simulações) leva ~15 s.
- Usar a mesma semente (mesmos choques) ao comparar alternativas.
- Limitações a declarar: retornos reais (sem inflação estocástica), sem custos/impostos, sem fase de retirada, drawdown medido em base mensal.
