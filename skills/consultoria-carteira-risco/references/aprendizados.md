# Aprendizados da sessão de construção (nov/2026)

## Erros encontrados nos textos-fonte
- **Cap. 6.3.8:** diz que o retorno necessário é "aproximadamente 4,5% a.a. real". O cálculo dá **6,84%**; a 4,5% o patrimônio final é R$ 768.824. Com 6,84% a carteira do exemplo (2,5% real) está bem mais atrás da meta do que o texto sugere.
- **Exemplo de Monte Carlo (cliente de 35 anos, R$ 5 mi):** o texto fala em 65% de chance. Com as próprias premissas (60/30/10, 9/4/5% reais, vols 16/6/10%, R$ 200 mil + R$ 1.000/mês, 30 anos) a simulação dá **6,5%**; a mediana é R$ 2,44 mi e o cenário de retorno médio fixo dá R$ 2,76 mi. Aporte de R$ 4.358/mês seria necessário para 70% de chance.
- Moral: sempre calcular e dizer ao Daniel quando um número do texto não fecha.

## Resultados de referência (premissas do texto)
- Rebalancear: sem rebalancear a mediana final é maior (R$ 2,55 mi vs R$ 2,44 mi), mas P(queda > 30%) vai de 11,3% para 21,9%. Banda de 5 p.p. dá o mesmo resultado do anual com ~12 operações em 30 anos em vez de 30.
- Risco de sequência: ações −30%, −10%, 0% nos últimos 3 anos derrubam a mediana a R$ 1,65 mi; nos 3 primeiros, a R$ 1,97 mi.
- Alocação tática +5 p.p. em ações (65/25/10): retorno esperado +0,25 p.p., volatilidade 10,5% → 11,2%, P(queda > 30%) 11,3% → 16,7%.
- Volatilidade maior eleva P(meta) de uma meta na cauda direita (6,5% → 8,7%) mas piora P10 (R$ 1,40 mi → R$ 1,20 mi) e P(queda > 30%) (11,3% → 38,5%).
- Caudas pesadas (t de Student, 5 g.l.) mudam pouco o resultado final em 30 anos, mas aumentam os extremos mensais.

## DIVO11 vs BRAX11 (exemplo, 31/ago a 11/nov/2026, 49 retornos diários)
- Correlação 0,98: na prática o mesmo risco de mercado. Volatilidade anual 39,2% (DIVO11) vs 40,1% (BRAX11); drawdown 20,1% vs 20,8%.
- Ambos caíram mais de 13% em 26/out/2026 (dia que domina a janela; sem ele a volatilidade cai para ~24%). A causa não foi verificada.
- Na carteira 70% CDI + 30% ETF: volatilidade 11,8% vs 12,0%; drawdown 5,8% vs 6,1%. Dividir entre os dois não diversifica.
- Conclusão para o consultor: escolher entre os dois quase não muda o risco; o que muda é o **peso total em ações**.
- Limite: janela curta e só retorno de preço (sem proventos).

## Fontes de dados: o que funcionou e o que não
- Acesso direto (curl) a Yahoo Finance e api.bcb.gov.br foi bloqueado pelo proxy do ambiente em nuvem.
- **Funcionou:** Firecrawl Alexandria `bcb-gov-br / economic-data/sgs_series` (CDI diário = código 12, IPCA mensal = 433, Selic meta = 432; janela diária limitada a 10 anos); `firecrawl_scrape` da página `stockanalysis.com/quote/bvmf/<TICKER>/history/` (≈ 50 pregões, sem ajuste de proventos).
- **Não funcionou:** capability `securities/price_history` da stockanalysis para ativos B3 (o símbolo `bvmf/DIVO11` não passa na validação); `firecrawl_interact` para trocar o período estourou o tempo.
- Para histórico longo, pedir ao Daniel um CSV de fechamento diário ajustado por proventos (B3, corretora ou terminal).

## Publicação dos relatórios
- O app da sessão pode não abrir os HTMLs gerados no contêiner. Solução que funcionou: publicar como Artifact privado (arquivo sem `<!doctype>/<html>/<head>/<body>`, `<title>` curto) e dar o link.
- Pastas do computador do Daniel (ex.: `D:\OneDrive\Daniel_Memoria`) podem não estar disponíveis para sessões na nuvem; nesse caso entregar um .zip para ele copiar.
- Não commitar `__pycache__` (há `.gitignore`).

## Usufruto (decumulação): lições de método
- Replique primeiro a tabela do plano do cliente com a fórmula V[t+1] = V[t]*(1+r) - 12*retirada. Se bater no centavo, o plano é "retorno constante, retirada no fim do ano", sem risco nem sequência. Conferir assim evita discutir número que não fecha.
- Convenção anual (retirada no fim do ano) dá meio ano de rendimento a mais sobre cada retirada; com retirada mensal no início do mês o mesmo plano fica sem folga. A "sobra" no fim do plano costuma ser só efeito de convenção.
- Probabilidade de sucesso de um plano determinístico que termina perto de zero é baixa (≈40% com retorno igual ao assumido): a retirada sustentável com 90% de chance é bem menor que a do cenário constante.
- Taxa de retirada acima de ~4-5% ao ano para quem tem 50+ anos pede ajuste de retirada, de horizonte ou de retorno. A volatilidade do portfólio muda pouco esse quadro; reduzir volatilidade sem reduzir retirada não resolve.
- Benchmark é régua de retorno, não de risco. Baixar a meta (ex.: IPCA+4) só reduz volatilidade se a composição mudar (menos duration, menos prefixado e ações). Sempre comparar a meta com o que o mercado paga (NTN-B e CDI no dia) e com a taxa líquida de IR.
- NTN-B levada ao vencimento garante a taxa de compra, mas NÃO tira a volatilidade (a marcação a mercado continua). ETF de duração constante (IMA-B5, IRF-M) cumpre papel parecido, sem a previsibilidade de vencimento, o que pode aumentar ou diminuir o ganho. O Daniel não gosta de travar taxa: não propor escada de NTN-B como solução; modelar a carteira por retorno e volatilidade médios.
- Dia de choque (ex.: 26/10/2026): medir a contribuição de cada posição no retorno do dia (peso × retorno). Posições pequenas e voláteis (ações) podem pesar como grandes posições de renda fixa de juros.
- Taxas de mercado em 13/11/2026 (Tesouro Direto): IPCA+ 2032 = 7,70%, 2040 = 7,46%, 2050 = 7,50%; Selic meta 13,75%; CDI ≈ 13,65% a.a.; IPCA 12 meses = 4,63%.

## Correções de entendimento (Daniel, nov/2026)
- **CONGELADO** na planilha da Portfel significa que o produto não recebe NOVOS aportes; não é reprovação. Posição existente é permitida. O validador só dá erro para dinheiro novo (`--novo-aporte`, e sempre nas carteiras-modelo).
- O estudo interno do benchmark IPCA+4 é o **"Backtest Carteiras Portfel"** (HTML). Uma cópia está no OneDrive pessoal em Daniel_Memoria/portfel/Investimentos (6 MB). Ler por anexo no chat, não pelo conector, para não encher o contexto.
- Retirar tudo no início do ano (vs mensal) reduz a chance de o dinheiro durar (ex.: 41% → 32% com IPCA+6 e vol 5%): a frequência combinada importa.
