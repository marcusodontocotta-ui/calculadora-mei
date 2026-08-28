# NEGÓCIO — Calculadora MEI

**Produto:** Calculadora DAS + gestão (vendas, despesas, estoque, clientes, limite R$ 81k)
**Modelo:** Freemium + PRO R$ 9,90/mês via Mercado Pago
**Mercado:** 22 milhões de MEIs no Brasil
**Status hoje:** 1 assinante pago (cliente **teste**, validado; funil real de mercado ainda NÃO validado)
**Base:** Cúpula de Gestão Autônoma — Time de Marketing
**Última atualização:** ago/2026 — cenários simulados para 3, 6 e 12 meses

---

## 1. Resumo executivo (números que importam)

| Indicador | Valor |
|---|---|
| Preço atual (PRO) | R$ 9,90/mês |
| Custo fixo mensal (Plano A) | R$ 0–5 (Render free + domínio ~R$ 60/ano) |
| Custo variável por assinante (tarifa + inadimplência) | ~R$ 0,70 (≈7%) → margem líquida ~92–94% |
| Break-even de caixa (Plano A) | **Mês 1** (1 assinante já cobre o custo ~zero) |
| Break-even com ads ligadas (Plano B, R$ 400–600/mês) | **43–65 assinantes ativos** (meta de 51 do LANCAMENTO fica no meio do intervalo → **validada**) |
| Payback por assinante (CAC R$ 25–50) | 2,7–5,4 meses |
| Churn mensal estimado (assinaturas mensais) | 4–8% |
| LTV (receita por assinante, 12 meses) | R$ 78–96 brutos (R$ 73–90 líquidos) |
| LTV lifetime (1/churn) | R$ 124–248 brutos |

**Projeção de MRR (fim do mês, bruto):**

| Cenário | Conv. visitante→PRO | Churn | 3 meses | 6 meses | 12 meses | Receita bruta em 12m |
|---|---|---|---|---|---|---|
| Conservador | 0,5% | 8% | R$ 185 | R$ 592 | R$ 1.781 | ~R$ 9.330 |
| Realista | 1,0% | 6% | R$ 768 | R$ 2.562 | R$ 8.596 | ~R$ 42.035 |
| Otimista | 2,0% | 4% | R$ 2.999 | R$ 11.845 | R$ 44.428 | ~R$ 208.600 |

> Leitura honesta: o produto fica **positivo em caixa desde o mês 1** em todos os cenários (custo quase zero).
> O que define sucesso não é "zerar prejuízo", e sim: **(a)** validar pagamento de estranhos, **(b)** escalar MRR para pagar o tempo do fundador (cenário realista cruza ~R$ 2.500/mês de MRR no M6) e **(c)** domar o churn.

---

## 2. Premissas do modelo (transparentes, para serem refutadas)

**Tráfego mensal por cenário** (orgânico; otimista inclui ads leves a partir do M6):

| Mês | Conservador | Realista | Otimista |
|---|---|---|---|
| 1 | 800 | 1.500 | 2.500 |
| 2 | 1.200 | 2.500 | 5.000 |
| 3 | 1.800 | 4.000 | 8.000 |
| 4 | 2.500 | 5.500 | 12.000 |
| 5 | 3.200 | 7.000 | 16.000 |
| 6 | 4.000 | 8.000 | 20.000 |
| 7 | 4.600 | 9.500 | 24.000 |
| 8 | 5.200 | 11.000 | 28.000 |
| 9 | 5.800 | 12.500 | 32.000 |
| 10 | 6.200 | 13.500 | 34.000 |
| 11 | 6.200 | 15.000 | 36.000 |
| 12 | 6.500 | 17.000 | 40.000 |

- Realista = execução média-boa do plano do LANCAMENTO (1.500 visitas no M1, ~4.000 acumulado no M2 — alinhado à meta do plano).
- Otimista = 1 vídeo viral + SEO top-3 em "calculadora DAS MEI"/"valor DAS MEI" + ads a partir do M7.
- **Sazonalidade:** janela de ouro do MEI é nov–fev (atualização anual do DAS, buscas em alta). Se a execução continuar, espere aceleração extra no M4–M6 e não necessariamente linearidade. Não embutei esse bônus nas tabelas.

**Funnel (visitante → PRO):** a conversão direta visitante→PRO de 1% (realista) assume, na prática, algo como: 20% dos visitantes se cadastram free × 4–6% de conversão free→PRO + retorno dos que usam o site sem cadastro. O 0,5% (conservador) cobre execução fraca de captura; o 2% (otimista) exige CTA forte + período de pico sazonal.

**Churn:** 8% conservador (mal onboarding), 6% realista (meta do plano, alcançada com onboarding + valor mensal), 4% otimista (plano anual + relatório mensal de lucro entregue por e-mail).

---

## 3. Projeção de receita — detalhe mensal

Modelo: `ativos(n) = ativos(n-1) × (1 − churn) + novos(n)`, com base inicial = 1 (cliente teste).

### 3.1 Consumidores ativos (fim do mês)

| Mês | Conservador | Realista | Otimista |
|---|---|---|---|
| 1 | 5 | 16 | 51 |
| 2 | 11 | 40 | 149 |
| 3 | 19 | 78 | 303 |
| 4 | 30 | 128 | 531 |
| 5 | 43 | 190 | 830 |
| 6 | 60 | 259 | 1.196 |
| 7 | 78 | 338 | 1.629 |
| 8 | 98 | 428 | 2.123 |
| 9 | 119 | 527 | 2.678 |
| 10 | 140 | 631 | 3.251 |
| 11 | 160 | 743 | 3.841 |
| 12 | 180 | 868 | 4.488 |

### 3.2 MRR (R$, bruto, fim do mês)

| Mês | Conservador | Realista | Otimista |
|---|---|---|---|
| 1 | 49 | 158 | 505 |
| 2 | 104 | 396 | 1.474 |
| 3 | 185 | 768 | 2.999 |
| 4 | 294 | 1.267 | 5.255 |
| 5 | 429 | 1.884 | 8.213 |
| 6 | 592 | 2.562 | 11.845 |
| 7 | 773 | 3.349 | 16.123 |
| 8 | 968 | 4.237 | 21.022 |
| 9 | 1.178 | 5.221 | 26.517 |
| 10 | 1.391 | 6.244 | 32.188 |
| 11 | 1.586 | 7.354 | 38.029 |
| 12 | 1.781 | 8.596 | 44.428 |

### 3.3 Receita bruta acumulada 12 meses

| Cenário | 3m | 6m | 12m |
|---|---|---|---|
| Conservador | R$ 338 | R$ 1.653 | **R$ 9.330** |
| Realista | R$ 1.322 | R$ 7.034 | **R$ 42.035** |
| Otimista | R$ 4.978 | R$ 30.291 | **R$ 208.600** |

Líquido dos 12m (desconta ~7% de tarifa/inadimplência): **conservador ~R$ 8.700 | realista ~R$ 39.100 | otimista ~R$ 194.000**.

**Ponto de atenção (realista):** MRR de R$ 8.596 no M12 exige ~868 assinantes e 17 mil visitas/mês. É um SaaS vivo, mas factível para uma ferramenta que dispute a palavra-chave "calculadora DAS MEI" (volume intenção alta, pico anual em dez–jan). Se o SEO não rankear top-5 até o M6, o cenário "realista" na verdade vira o "conservador" — por isso os gates da seção 7.

---

## 4. Break-even e payback (atualizado)

### 4.1 Break-even de caixa — Plano A (custo ~zero)
Custo fixo = R$ 0–5/mês (Render free; domínio ~R$ 5/mês quando adquirido).
**Break-even: 1º assinante.** Já coberto inclusive pelo cliente teste. Não é o gargalo.

### 4.2 Break-even do plano com ads — Plano B (R$ 400–600/mês)
Custo fixo R$ 400–600. Receita líquida por assinante ~R$ 9,20.
`Break-even = custo fixo ÷ receita líquida/assinante = 43 a 65 assinantes ativos`.

**Meta de 51 do LANCAMENTO validada como ponto de equilíbrio do cenário com publicidade.**

Quando cada cenário cruza a marca de 51 ativos:
| Cenário | Mês (aprox.) |
|---|---|
| Conservador | M5–M6 |
| Realista | M3 |
| Otimista | M2 |

### 4.3 Payback
| Tipo | Cálculo | Resultado |
|---|---|---|
| Payback do projeto (Plano A) | investimento ~R$ 0 | Imediato |
| Payback por assinante (CAC R$ 25) | 25 ÷ 9,20 | ~2,7 meses |
| Payback por assinante (CAC R$ 50 = teto do plano) | 50 ÷ 9,20 | ~5,4 meses |
| Regra de corte saudável | payback ≤ 6 meses (= LTV/CAC ≥ 3,3) | CAC máx. R$ 55 |

### 4.4 O break-even que realmente importa (tempo do fundador)
Com o fundador dedicando 20–40h/semana, o custo real é o de oportunidade. Para pagar uma remuneração mínima (~R$ 2.500/mês):
- **Conservador:** não atinge em 12 meses (MRR R$ 1.781 no M12).
- **Realista:** atinge entre M6 e M7 (MRR R$ 2.562→3.349).
- **Otimista:** atinge no M3 (MRR R$ 2.999).

Conclusão prática: se em 6 meses não estiver no caminho "realista", o projeto é válido como renda secundária pequena, não como negócio de tempo integral.

---

## 5. CAC por canal e regra para escalar

| Canal | Custo | CAC efetivo | Observação | Regra para escalar |
|---|---|---|---|---|
| Grupos Facebook/WhatsApp | R$ 0 (30min/dia) | R$ 0–5 (só tempo) | Regra 80/20; melhor conversão se responde dúvida com a ferramenta | Máximo = limite de tempo (≈ dias de postagem); não tem custo $$
| TikTok / Reels / Shorts | R$ 0 (produção) | R$ 0–10 | 0,5–2% de visitas; alto potencial de viral no tema "limite do MEI" | Impulsionar APENAS vídeos com retenção/CTR já provados organicamente. Sem repetir impulsionamento de fracasso |
| SEO + Google Meu Negócio | R$ 0 (+R$ 5/mês domínio) | R$ 0 marginal (custo é tempo/rank) | Compounding; caça "calculadora DAS MEI ano 2026" | Sempre ligado. Gate: rankear top-5 em 3 kw-alvo até M6; senão redirecionar esforço |
| Parcerias contadores/SEBRAE | Comissão 30–50% do 1º mês | R$ 3–5 | Confiança instantânea; baixo charme de escala | Escalar ilimitadamente enquanto o parceiro indicar (CAC fixo em R$ 3–5). Meta 5 parcerias/30d |
| Reddit / fóruns | R$ 0 (tempo) | R$ 0–5 | Anti-spam; volume limitado por moderação | Não escala; usar como validação de mensagem, não como motor |
| Ads Meta (lead magnet) | R$ 300–500/mês | **R$ 25–50** (CPL R$ 2–5 × conversão 5–10% para PRO) | Começa só com CPL validado | **Gate rígido:** CAC < R$ 50 por 2 semanas consecutivas. Se falhar, pausar e voltar 100% ao orgânico |

### Regra geral de escala (uma linha)
> Aumentar budget de ads em +50% a cada 2 semanas **somente se** `CAC < R$ 45` **e** `payback < 4 meses`; pausar o canal que mostrar `CAC > R$ 55` (≈ LTV/3) por 2 semanas seguidas. Orçar 70% do budget no canal vencedor e 30% em experimentos.

---

## 6. Churn e LTV

### 6.1 Churn estimado (assinaturas mensais)
| Cenário | Churn mensal | Vida média (1/churn) | Fonte/fator |
|---|---|---|---|
| Conservador | 8% | 12,5 meses | Onboarding fraco, sem valor mensal percebido |
| Realista | 6% | 16,7 meses | Meta do LANCAMENTO (<8% em 60d, <10% inicial); onboarding + alertas |
| Otimista | 4% | 25 meses | 30–50% dos assinantes no plano anual |

### 6.2 LTV por assinante
| Métrica | Fórmula | Conservador (8%) | Realista (6%) | Otimista (4%) |
|---|---|---|---|---|
| Receita por assinante em 12 meses | Σ retenção × R$ 9,90 | R$ 78 | R$ 86 | R$ 96 |
| LTV líquido em 12 meses | −7% custos | R$ 73 | R$ 80 | R$ 89 |
| LTV lifetime (bruto) | R$ 9,90 ÷ churn | R$ 124 | R$ 165 | R$ 248 |
| LTV lifetime (líquido) | × 0,93 | R$ 115 | R$ 153 | R$ 231 |
| LTV/CAC com CAC R$ 25 | — | 4,6x | 6,1x | 9,2x |
| LTV/CAC com CAC R$ 50 | — | 2,3x | 3,1x | 4,6x |

> **Nota de guarda:** LTV lifetime de R$ 165–248 assume assinatura mensal estável por 16–25 meses — otimista para o público MEI de renda baixa. Use o LTV de 12 meses (R$ 73–89 líquidos) como referência de decisão de marketing, não o lifetime. Com CAC ≤ R$ 45, a matemática ainda é saudável.

---

## 7. Preço: R$ 9,90 está adequado?

### 7.1 Referências de valor no mercado
- DAS do MEI (serviço) ≈ R$ 76,90/mês — o produto custa **~13% do próprio DAS**.
- Contador MEI ≈ R$ 120–300/mês — preço é **~4–8% de um contador**.
- App gratuito do governo (Cálculo DAS) existe → a diferenciação precisa ser **gestão**, não só cálculo.
- Concorrentes "controladoria popular" (Conta Azul/Nibo/Bling) partem de R$ 30–60/mês → espaço abaixo disso é real, mas o público-alvo é mais sensível a preço.

**Veredito: R$ 9,90 é adequado como preço de entrada (âncora "R$ 0,29/dia", impulso de compra).**
É o "ticket de descoisão": baixo o suficiente para não gerar fricção, alto o suficiente para filtrar usuários sérios e gerar MRR não-trivial. Não é o preço final — é a porta de entrada.

### 7.2 Simulação de preços alternativos (elasticidade estimada)

Hub = conversão visitante→PRO de 1% a R$ 9,90. Estimativa realista de queda de conversão ao subir preço (público sensível):

| Preço | Δ preço | Conversão estimada | Receita/visitante | Δ vs R$ 9,90 | Payback (CAC R$ 25) | Payback (CAC R$ 50) |
|---|---|---|---|---|---|---|
| **R$ 6,90** | −30% | 1,3% (+30%) | R$ 0,090 | **−9%** | 2,9m | 5,8m |
| **R$ 9,90** (atual) | base | 1,0% | R$ 0,099 | base | 2,7m | 5,4m |
| **R$ 12,90** | +30% | 0,8% (−20%) | R$ 0,103 | **+4%** | 2,1m | 4,2m |
| **R$ 19,90** | +101% | 0,55% (−45%) | R$ 0,109 | **+11%** | 1,3m | 2,7m |

**Análise:** o melhor "dinheiro por visitante" está em R$ 12,90–19,90, mas isso SEM considerar que:
1. R$ 19,90 quebra a narrativa "menos que uma pizza" e o público MEI de renda baixa (faixa R$ 2–5 mil) é o mais conversor — é justamente onde o preço mais dói.
2. A receita por visitante assume conversão de visitante direto; na prática, subir preço reduz também cadastros free e volume de funil.

**Recomendação de preço:**
1. **Manter R$ 9,90 para novos assinantes no lançamento e durante a validação do funil (até ~100 assinantes reais).**
2. Testar **A/B a R$ 12,90** em 20–30% do tráfego pago logo que houver volume; se receita/visitante subir +10–15% com conversão ≥ 0,75%, migra o preço novo para novos assinantes (grandfathering na base atual).
3. **Não usar R$ 19,90** antes de empilhar valor real (ex.: emissão de NF-e simplificada, integração de notas, relatório de IR) que justifique a percepção de produto/gestor, não só calculadora.
4. **Preço maior + plano anual = combinação recomendada** (seção 8): o anual captura fluxo de caixa e retenção sem subir o ticket mensal percebido.

### 7.3 Impacto de preço na margem
| Preço | Custo variável (tarifa ~5% + inadim. ~2%) | Líquido/assinante | Margem líquida |
|---|---|---|---|
| R$ 9,90 | ~R$ 0,70 | ~R$ 9,20 | ~93% |
| R$ 12,90 | ~R$ 0,90 | ~R$ 12,00 | ~93% |
| R$ 19,90 | ~R$ 1,40 | ~R$ 18,50 | ~93% |

A margem (%) não muda com o preço (custo é %); o que muda é o **valor absoluto por assinante** e o **payback de CAC** — ambos melhoram com preço maior. A margem de ~93% é o ovo de ouro: o negócio inteiro é uma máquina de CAC + churn, não de custo de produto.

> A margem "98,7%" do LANCAMENTO só vale se a cobrança for via PIX (tarifa ~1–2%) — impliquei **94–95%** no cenário cartão de crédito (tarifa Mercado Pago ~5%). O número real deve sair da conciliação do webhook; monitore no primeiro trimestre de cobrança.

---

## 8. Upgrade de preços: plano anual com desconto

### 8.1 Oferta recomendada
| Plano | Preço | Equiv./mês | Desconto | Efeito caixa | Efeito retenção |
|---|---|---|---|---|---|
| Mensal | R$ 9,90 | R$ 9,90 | 0% | pagamento mensal | churn mensal 6% (base) |
| Semestral (opcional) | R$ 54,00 | R$ 9,00 | −9% | R$ 54 à vista | reduz churn do M6 |
| **Anual (principal)** | **R$ 99,00** | **R$ 8,25** | **−16,7%** ("2 meses grátis") | **R$ 99 à vista** | churn anual ~2–4%/ano (≈0,2%/mês) |
| Mensal × 12 (contrafactual) | R$ 118,80 | R$ 9,90 | — | parcelado | alto churn agregado |

**Como vender:** ofertar o anual como opção destacada no checkout ("Economize 2 meses — R$ 99/ano"), upgrade automático no cartão de crédito já existente (o Mercado Pago mantém o token), e promoções sazonais de conversão (dez–jan, pico de formalização de MEI).

### 8.2 Impacto em fluxo de caixa (cenário realista, M12 = 868 ativos)
| Composição | Assinantes | Receita imediata/recorrente |
|---|---|---|
| 20% anual (M12) | ~174 | R$ 17.226 **à vista** (174 × R$ 99) |
| 80% mensal | ~695 | R$ 6.881 **/mês** recorrentes |
| **Receita no M12** | **868** | **~R$ 24.100 no mês** (vs R$ 8.596 puro mensal) |

Com apenas 20% de mix anual, o fluxo de caixa do M12 quase triplica no mês de renovação/bloqueio anual. Isso funda investimento em ads sem esticar caixa.

### 8.3 Impacto em retenção e unidade econômica
- Churn mensal hipotético: 25% dos assinantes em plano anual (churn ~1–2%/ano) muda o churn ponderado de 6% para ~4,8% → LTV +20–25%.
- **Payback de CAC no anual:** CAC R$ 50 ÷ (R$ 99 × 0,93) ≈ **0,5 mês** — permite escalar ads agressivamente mesmo com CAC maior.
- Trade-off a vigiar: desconto −16,7% reduz em até 17% a receita dos que migrariam do mensal para anual. Isso é **barato** quando comparado a 6–8% de churn mensal evitado (o mensal "vaza" 100% da receita do mês seguinte; o anual "vaza" só no próximo ano).

### 8.4 Regras de implementação
1. **Grandfathering:** base atual mantém R$ 9,90mensal; aumento de preço vale só para novos (evita churn por "preço injusto").
2. **Garantia 7 dias** no anual (6,98% de troca é aceitável; reduz medo).
3. **A/B do plano anual** com incentivo: "R$ 79/ano na 1ª semana" × "R$ 99/ano" para calibrar elasticidade antes de fixar.
4. **Renovação:** lembrete +30/-7 dias; nunca "cobrar" sem aviso (evita assessor de chargeback de cancelamento involuntário).

---

## 9. Riscos principais e mitigações

| # | Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|---|
| 1 | **Funil real não validado** (1º pago é cliente teste) | Alta | Crítico | Marco explícito: **10 pagantes não-teste até o fim do M2** (ou R$ 150 MRR). Se não acontecer, revisar mensagem/UX antes de qualquer ads |
| 2 | Concorrência grátis (app da Receita / planilhas) | Alta | Médio-alto | Não vender "cálculo DAS"; vender **gestão + limite + lucro em 2 minutos**. Freemium já neutraliza parte |
| 3 | Churn alto no público de baixa renda (desiste após 1–3 meses) | Média | Alto | Plano anual (R$ 99), onboarding ativo, relatório mensal de lucro por e-mail, alertas de DAS com valor entregue todo mês |
| 4 | Dependência de SEO/tráfego orgânico (lento, sem ads no Plano A) | Alta | Médio | Meta 51 em 60d é difícil sem viral/parcerias. **Reduzir dependência:** converter a lista de e-mails (lead magnets) com ofertas sazonais. Vigiar M6: se MRR < R$ 1.500, não ligar ads |
| 5 | Infra Render free (sleep, throttling, sem domínio seguro para SEO) | Média | Médio | Upgrade para Render Starter (~R$ 25/mês) quando MRR > R$ 200; registrar domínio (~R$ 60/ano) até o M3 para SEO |
| 6 | Tarifas/chargeback Mercado Pago e inadimplência maiores que o previsto (modelo usa ~7%) | Média | Médio | Conciliação mensal do webhook; cobrar preferencialmente PIX (tarifa menor); política de re-trial para inadimplentes |
| 7 | Mudança regulatória do teto/DAS (2026–27) | Baixa | Médio | Código parametrizado (TABELA_DAS_*); atualização anual automática = oportunidade de SEO ("tabela do ano novo") |
| 8 | Sazonalidade (pico nov–fev vs vale mar–out) dá impressão de estagnação | Média | Médio | Ler métricas em série móvel de 3 meses; campanhas de re-engajamento no vale |
| 9 | Preço/prêmio: subir preço antes de valor percebido quebra a fórmula | Média | Médio | Subir para R$ 12,90 só após R$ 12,90 provar receita/visitante maior em A/B; nunca para "ganhar sem mudar produto" |
| 10 | Tempo do fundador (custo de oportunidade) | Alta | Alto | Gate de 6 meses da seção 4.4: se não houver caminho realista, definir teto de horas e reavaliar |

---

## 10. Decisões e próximos marcos

| Prazo | Marco mensurável | Decisão disparada |
|---|---|---|
| M1 (set/26) | 10 pagantes não-teste; 800–1.500 visitas | Validar/escolher mensagem vencedora vs UX vencedora |
| M2 (out/26) | 51 ativos (break-even Plano B) OU CAC medido no orgânico | Ligar ads só se funil validado |
| M3 (nov/26) | MRR ≥ R$ 750; domínio + Starter; primeiro plano anual (meta 10%) | Iniciar A/B de preço R$ 12,90 em 20% do tráfego |
| M4–M6 (dez–fev) | Janela sazonal de MEI; MRR realista ≥ R$ 2.500; CAC < R$ 45 | Calibrar desconto do plano anual; decidir subida de preço |
| M9–M12 | MRR ≥ R$ 8.000 no caminho realista | Avaliar: produto 2.0 (NF-e), contratação para produção de conteúdo, ou monetização adicional |

**Três regras de disciplina financeira:**
1. **Nunca** gastar mais de R$ 600/mês em ads antes de MRR ≥ R$ 1.500 (não negocie com dinheiro que você não tem provando que o funil funciona).
2. **Sempre** reinvestir ≤ 50% do MRR novo em aquisição; o resto é caixa/reserva.
3. **Sempre** reconciliar webhook × conciliação bancária mensalmente (margem real é o que define tudo).

---

## Anexo — Parâmetros usados

| Parâmetro | Valor |
|---|---|
| Preço PRO | R$ 9,90/mês |
| Custo variável agregado | 7% do ticket (5% tarifa cartão + 2% inadimplemento/reserva) |
| Custo fixo Plano A | R$ 0–5/mês |
| Custo fixo Plano B | R$ 400–600/mês (ads) |
| Conversão visitante→PRO | 0,5% / 1,0% / 2,0% |
| Churn mensal | 8% / 6% / 4% |
| Base inicial | 1 assinante (cliente teste) |
| DAS de referência (serviço) | ~R$ 76,90/mês |
| Contador de referência | ~R$ 150/mês |