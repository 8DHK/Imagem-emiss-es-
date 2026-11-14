# Planilha de ativos diligenciados da Portfel (formato visto em mar/2026)

Arquivo: "Planilha de Fundos V4.xlsx" (título interno: "Planilha de ativos diligenciados Março - 2026").
É uma planilha de **elegibilidade e regras**, não de desempenho. Os valores (percentuais, limites, produtos) ficam
na planilha; não copie para repositórios. Leia o arquivo atual a cada uso, pois ele muda por versão.

## Abas e o que cada uma traz
- **Composições** (oculta): por perfil (Conservador, Moderado, Equilibrado, Arrojado, Agressivo), limites por classe
  (mínimo, recomendado, máximo, e mínimo/máximo do grupo) e as carteiras-modelo ("Conservador Geral", "Conservador Qualificado" etc.).
- **Conservador / Moderado / Equilibrado / Arrojado / Agressivo**: alocação máxima por ativo conforme o perfil e o
  patrimônio líquido informado na célula, mais a carteira recomendada (produto, classe, % do PL, liquidez, taxa, rating).
- **Produtos Autorizados** (~260 produtos): CNPJ/ticker, ISIN/ANBIMA, nome, classe de ativo, classificação ARCA,
  **risco (Baixo/Médio/Alto)**, alocação máxima, rating (A/B/C), tipo (fundo, ETF, FIDC, Tesouro, carteira, FI-Infra, FMP),
  estratégia (gestão ativa ou indexado), taxas, tributação, liquidação (D+x), tipo de investidor (Geral/Qualificado), observações.
- **Previdências**, **Alternativos** (private equity/debt), **Manutenção de CP** (crédito privado só para manutenção),
  **Ranking BC** (bancos por classe S1 a S5: limites de alocação, FGC), **Carteiras - Finclass** (carteiras de ações liberadas em
  conjunto), **Busca de Fundos**, **Menu**.

## Tipos de regra a validar em qualquer carteira
1. Limite por classe de ativo e por perfil (mín./máx. da classe e do grupo).
2. Limite por produto (coluna "Alocação Máx."), por FIDC/private equity, por gestão ativa e por gestora.
3. Vetos por perfil (ex.: FIDC para conservador) e por tipo de investidor (Geral vs Qualificado).
4. Preferência por rating A ou B; produtos "CONGELADO" não recebem aporte.
5. Bancos: limites por faixa S1 a S5 e limite do FGC por emissor.
6. Carteiras Finclass e alternativos: só em conjunto / com limites próprios.
7. Risco Baixo/Médio/Alto é definido por **queda histórica** (faixas de drawdown): serve de régua de risco do produto.

## O que a planilha NÃO tem (preencher de outra fonte)
- Retorno esperado, volatilidade, drawdown e correlações por produto.
- Série histórica de cotas/rentabilidade. Para fundos há o CNPJ, então o caminho é o Informe Diário da CVM
  (dados abertos) ou uma exportação de terminal/plataforma que o Daniel tenha. Sem isso, usar premissas por classe
  (retorno real e volatilidade por classe) e declarar que são estimativas.
