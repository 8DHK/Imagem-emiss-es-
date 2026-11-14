---
name: consultoria-carteira-risco
description: Use ao montar ou revisar a carteira de um cliente de consultoria de investimentos (Portfel) e ao medir ou simular risco. Cobre relatório de performance (TWR/MWR, volatilidade, drawdown, Sharpe/Sortino/beta, atribuição alocação x seleção, retorno necessário vs atual), simulação de Monte Carlo (probabilidade de atingir a meta, leque de resultados, risco de sequência, alavancas), comparação do efeito de ativos no risco da carteira (ex.: DIVO11 vs BRAX11) e rebalanceamento/alocação tática. Acionar quando Daniel compartilhar a planilha de ativos da Portfel, pedir "monte uma carteira", "simule", "relatório de performance", "esse ativo aumenta o risco?" ou "qual a chance de o cliente chegar na meta". Não é para mensagens de WhatsApp a clientes (my-writing-style) nem para leads frios (lead-dialogue).
---

# Carteira, performance e risco (consultoria de investimentos)

Ajuda o Daniel (consultor na Portfel) a montar a carteira de um cliente e a mostrar, com números, o risco e a chance de atingir o objetivo. Tudo é **material de apoio para o consultor revisar**: a escolha final dos ativos, a adequação ao perfil (suitability) e qualquer comunicação ao cliente são do Daniel.

## Quando não usar
- Redigir mensagem de WhatsApp para cliente ativo: usar `my-writing-style`.
- Conversa com lead frio: usar `lead-dialogue`.

## Entradas (peça o que faltar, nunca invente)
1. **Planilha de ativos da Portfel** (diligenciada por eles). Formato de referência em `assets/modelo_ativos.csv`; histórico mensal opcional em `assets/modelo_historico_mensal.csv`. A planilha real pode ter outras colunas: mapeie com o Daniel e diga o que foi estimado.
2. **Cliente:** objetivo (valor em R$ reais), prazo, patrimônio inicial, aporte mensal, perfil e **perda máxima tolerada**.
3. **Restrições:** liquidez, limite por ativo e por emissor, classes aceitas/vetadas, tributação.
4. **Premissas de retorno real** (ex.: CDI e IPCA esperados) e regra de rebalanceamento (calendário ou banda).

Dados do cliente chegam anonimizados (sem nome e CPF). Se vierem identificáveis, trate como confidencial, não os copie para arquivos de exemplo e avise o Daniel. A planilha da Portfel é proprietária: o Daniel decide se pode compartilhá-la.

## Fluxo
1. **Validar os dados.** `python3 scripts/carregar_ativos.py ativos.csv [historico.csv]` lista retorno, volatilidade e correlações e emite AVISOS (histórico curto, volatilidade estimada, correlação por premissa). Repasse os avisos ao Daniel.
2. **Montar 2 ou 3 carteiras candidatas** que respeitem as restrições. Para cada uma: pesos, justificativa por ativo, retorno real esperado, volatilidade, concentração por ativo/emissor, liquidez.
3. **Simular** com `scripts/monte_carlo.py` (API em `references/formulas.md`). Entregue: probabilidade de atingir a meta, percentis (P5, P10, P50, P90, P95), mediana **e** média, probabilidade de queda máxima > 20/30/40%, risco de sequência (choque no início vs no fim), alavancas (aporte para 70% de chance, meta compatível com 70%, alocação), sensibilidade (retornos −1 p.p., volatilidade +20%, caudas pesadas, correlações de crise 0,8) e rebalanceamento (nenhum, anual, banda 5 p.p.).
4. **Comparar ativos** quando perguntado "qual aumenta o risco?": correlação com a carteira, drawdown e volatilidade da carteira com cada ativo, e peso máximo dentro do drawdown tolerado (`scripts/comparar_ativos.py` é o modelo).
5. **Relatório** em HTML seguindo o capítulo 6.3 (ver abaixo). Modelos prontos: `scripts/gerar_relatorio.py` (performance) e `scripts/simulacao_monte_carlo.py` com `simulacao_monte_carlo_template.html` (Monte Carlo). Rode com `python3 scripts/<script>.py caminho/saida.html`.
6. **Entrega:** resumo curto no chat (resultado, o que decidir, limites) e o relatório publicado. Ao publicar como Artifact, remova `<!doctype>`, `<html>`, `<head>` e `<body>` do arquivo e deixe só `<title>` (nome curto, sem "— explicação") e `<style>`. Sem scripts externos.

## Estrutura do relatório de performance (cap. 6.3)
Três blocos, sempre na mesma ordem e formato:
1. **Contexto do plano:** meta, prazo, retorno real necessário (calculado), perfil, drawdown tolerado, alocação-alvo, liquidez e tributação.
2. **Evolução frente à meta:** trajetória acumulada vs linha do retorno necessário (com 100% renda fixa e 100% ações só como referência) e faixa de viabilidade (pessimista, realista, otimista).
3. **Análise e recomendações:** retorno por período (mês, trimestre, ano, 12 meses, desde o início) em TWR, MWR e real; risco; contribuição por classe; alocação x seleção; alavancas de ajuste.
Foco na **meta**, não no benchmark. Um objetivo por gráfico, e cada gráfico com tabela de dados alternativa.

## Regras que não podem falhar
- **Calcule, nunca copie.** O retorno necessário e a probabilidade de atingir a meta saem de cálculo. Os textos-fonte trazem números errados (ver `references/aprendizados.md`).
- **Dados fictícios sempre marcados** no relatório ("Dados fictícios") e nunca apresentados como do cliente.
- **Probabilidade de meta nunca sozinha.** Mostre junto o P10 e a probabilidade de queda grande: volatilidade maior pode *aumentar* P(meta) de uma meta na cauda direita e piorar o lado ruim.
- **Rebalancear reduz risco, não aumenta retorno mediano.** Não venda como ganho de retorno.
- **Janela curta não é conclusão.** Com menos de ~36 meses, ou com um único dia dominando o resultado, diga que é leitura preliminar.
- **Retorno de preço ≠ retorno total.** Fontes como stockanalysis.com não ajustam proventos (ex.: DIVO11). Diga quando isso distorce.
- **Sem promessa de resultado.** Inclua: rentabilidade passada não garante rentabilidade futura; projeções são cenários.
- Fonte de dados dos números sempre explícita (planilha da Portfel, estimativa, premissa do Daniel).

## Scripts (Python 3, requer numpy)
- `scripts/monte_carlo.py`: motor (Cholesky, retornos log-normais mensais, aportes, rebalanceamento anual/banda/nenhum, choques de sequência). Rode a partir da pasta `scripts/`, **sem** a flag `-I`, pois os scripts importam `monte_carlo` localmente.
- `scripts/carregar_ativos.py`: lê a planilha no formato do modelo e devolve `mu`, `sig`, `corr`. Para N ativos use `normais(k=N)` e `t_student(k=N)`.
- `scripts/gerar_relatorio.py`, `simulacao_monte_carlo.py`, `comparar_ativos.py`: implementações de referência com os dados fictícios do exemplo. Para um cliente real, troque as séries e premissas pelas do cliente em vez de reescrever a lógica.
- A ligação automática "planilha real → carteira → relatório" ainda não está em um único script: o Claude monta as carteiras com `carregar_ativos.py` + `monte_carlo.py` e adapta o relatório de referência.

## Fontes de dados públicas (limites vistos)
Ver `references/aprendizados.md`: o que funcionou (BCB/SGS via Firecrawl, página de histórico da stockanalysis.com) e o que não (acesso direto ao Yahoo/BCB bloqueado no ambiente em nuvem; página mostra só ~50 pregões).
