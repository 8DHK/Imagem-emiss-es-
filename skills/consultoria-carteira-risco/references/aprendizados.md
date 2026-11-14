# Aprendizados de método (instruções, sem dados de cliente)

## Fontes de dados públicas: o que funciona e o que não
- Funciona: Firecrawl Alexandria `bcb-gov-br / economic-data/sgs_series` (CDI diário = 12, IPCA mensal = 433, Selic meta = 432; janela diária de até 10 anos); página de rendimento dos títulos do Tesouro Direto via `firecrawl_scrape` (taxas IPCA+ do dia); página de histórico da stockanalysis.com via `firecrawl_scrape` (≈ 50 pregões, sem ajuste de proventos).
- Não funciona: acesso direto (curl) a Yahoo Finance e api.bcb.gov.br no ambiente em nuvem; `securities/price_history` da stockanalysis para ativos da B3 (o símbolo não passa na validação); `firecrawl_interact` para trocar o período (estoura o tempo).
- Histórico longo: pedir ao Daniel um CSV de fechamento diário ajustado por proventos. Sempre buscar as taxas de mercado do dia em vez de reutilizar números antigos.

## Entrega e confidencialidade
- Relatório com dados de cliente: publicar como Artifact privado, com o nome do cliente omitido. Para publicar, o arquivo vai sem `<!doctype>`, `<html>`, `<head>` e `<body>`, e com `<title>` curto.
- Nada particular vai para o GitHub: só a instrução do estudo (skill, scripts genéricos, modelos fictícios). Configs, planilhas, extratos e HTMLs de cliente ficam fora do git (`config.json` do cliente, `dados_portfel/`, `*.xlsx`).
- Pastas do computador do consultor podem não estar disponíveis para sessões na nuvem; arquivos pesados ou de outro OneDrive: pedir o anexo no chat. Não commitar `__pycache__`.

## Risco e simulação
- Calcular, nunca copiar números dos textos-fonte: retorno necessário e probabilidade da meta divergiram do texto nas duas ocasiões em que foram recomputados.
- Rebalancear reduz risco, não aumenta o retorno mediano.
- Probabilidade da meta nunca sozinha: mostrar P10 e a probabilidade de queda grande. Volatilidade maior pode aumentar a chance de atingir uma meta na cauda direita e piorar o lado ruim.
- Janela curta ou dominada por um dia é leitura preliminar. Retorno de preço não é retorno total (proventos).

## Usufruto (decumulação)
- Replicar primeiro a tabela do plano com V[t+1] = V[t]*(1+r) - 12*retirada. Se bater no centavo, o plano é retorno constante com retirada no fim do ano, sem risco nem sequência.
- Convenção anual dá meio ano de rendimento a mais sobre cada retirada; com retirada mensal no início do mês o mesmo plano fica sem folga.
- Plano determinístico que termina perto de zero tem chance de sucesso baixa na simulação. A retirada sustentável com 90% de chance é bem menor que a do cenário constante.
- Conferir a taxa de retirada (retirada anual ÷ patrimônio) e o horizonte antes de falar em volatilidade.
- Benchmark é régua de retorno, não de risco. Comparar a meta com o que o mercado paga no dia e com a taxa líquida de IR.
- NTN-B levada ao vencimento garante a taxa de compra, mas não tira a volatilidade (a marcação a mercado continua). ETF de duração constante (IMA-B5, IRF-M) cumpre papel parecido, sem a previsibilidade de vencimento, o que pode aumentar ou diminuir o ganho. O Daniel não gosta de travar taxa: não propor escada de NTN-B; modelar por retorno e volatilidade médios.
- A frequência da retirada importa: tirar o valor anual de uma vez no início do ano reduz a chance de o dinheiro durar.
- Em dia de choque, medir a contribuição de cada posição (peso × retorno do dia): posição pequena e volátil pode pesar como uma grande de juros.

## Planilha de ativos da Portfel
- CONGELADO significa que o produto não recebe novos aportes; não é reprovação. Posição existente é permitida. O validador só dá erro para dinheiro novo (`--novo-aporte`, e sempre nas carteiras-modelo).
- Ao validar as carteiras-modelo, podem aparecer inconsistências da própria planilha: avisar o Daniel em vez de corrigir sozinho.

## Erros de processo a evitar
- Não comece a calcular um estudo sem fazer o briefing (`references/briefing.md`): premissas minhas, inferências de anotações e leituras de gráfico viraram "dados" sem confirmação.
- Não deduza data de início, tolerância a perda nem a natureza de um fluxo (aporte, vencimento reinvestido, retirada): pergunte.
- Os números dos relatórios de exemplo são fictícios e não pertencem a nenhum cliente.
