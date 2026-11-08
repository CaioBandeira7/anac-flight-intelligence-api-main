# Catálogo de visualizações

Inventário exaustivo do código em `22a120a` e da apresentação revisada: **26 gráficos na web**,
**4 tabelas por horizonte**, **16 KPIs**, **7 painéis/status do registro de modelos** e **37 figuras no relatório**. PNG e SVG do mesmo gráfico
contam como uma figura, não duas. Reutilização de um componente entre modelos conta por instância
estatística, não por DOM montado simultaneamente (a web troca abas).
Não existe gráfico de previsão futura. Market/weekday estão no payload e na análise, mas não
são gráficos montados pelo ML Studio; a existência do campo não significa exibição.
Os controles de modelo, horizonte e exemplos, legendas, tooltips e avisos não são novos gráficos.
O Model registry abaixo do showcase é metadado/tabulação da API, não curva preditiva.

O ranking de entidades e os exemplos são diagnósticos retrospectivos. A seleção do horizonte
muda só a curva mensal; scatter e casos usam h=1, histogramas/decis/ranking/KPIs agrupam horizontes.
A tabela de horizonte explicita cada grupo. Nenhuma soma desses horizontes representa demanda
adicional independente. Fontes v1 preservadas podem conter texto anterior à errata da auditoria.

## web-a-monthly — Actual vs predicted, by target month

1. **Localização:** `web/components/dashboard/ml-showcase.tsx` TaskView / LinesChart.
2. **Modelo/experimento:** A.
3. **Objetivo:** Comparar nível observado, previsão de seleção e referência.
4. **Eixos, unidade e legenda:** X: janeiro a dezembro de 2023. Y: movements. Atual, LightGBM e melhor baseline global.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; monthly, filtrado por horizon; B usa assentos observados como pesos de todas as séries.
6. **Leitura estatística:** A proximidade de totais/médias avalia nível agregado, não igualdade por unidade. Lower is better; cor do modelo=chart-1/azul, baseline=muted/cinza; atual=ink; tokens DAY/NIGHT.
7. **Conclusão sustentada:** Revela desvios temporais e de nível do experimento selecionado.
8. **Limites e leituras incorretas:** Cancelamentos de erro podem ocultar falhas de rota/dia. Só este gráfico acompanha o seletor de horizonte; comparação fixa no melhor baseline agregado.

## web-a-volume — Error by traffic volume

1. **Localização:** `web/components/dashboard/ml-showcase.tsx` TaskView / LinesChart.
2. **Modelo/experimento:** A.
3. **Objetivo:** Inspecionar heterogeneidade do erro por tamanho histórico.
4. **Eixos, unidade e legenda:** X: decis 1–10 da feature SIZE conhecida no cutoff. Y: WAPE, %, modelo e baseline.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; by_volume_decile; níveis A=hist_level_56, B=hist_seats_mean_12, D=hist_pax/seats_mean_12.
6. **Leitura estatística:** Agrupa observações por feature histórica; limites dos decis são estimados em 2023. Lower is better; cor do modelo=chart-1/azul, baseline=muted/cinza; atual=ink; tokens DAY/NIGHT.
7. **Conclusão sustentada:** Sustenta diferenças descritivas de dificuldade entre estratos observados.
8. **Limites e leituras incorretas:** Não é WAPE por número de unidades nem ranking futuro. Decis não são limiares fixados no treino; os horizontes estão agrupados.

## web-a-entity — Largest units, by airport (ICAO)

1. **Localização:** `web/components/dashboard/ml-showcase.tsx` TaskView / PairBars.
2. **Modelo/experimento:** A.
3. **Objetivo:** Comparar modelo e regra nas maiores entidades observadas.
4. **Eixos, unidade e legenda:** Entidade no eixo categórico; comprimento horizontal= WAPE, %. Azul modelo, cinza baseline.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; by_entity[:10], agrupado por aeroporto A, companhia B ou rota D; tamanho por volume observado em 2023.
6. **Leitura estatística:** Ranking é retrospectivo e os erros são recalculados sobre as linhas de cada entidade. Lower is better; cor do modelo=chart-1/azul, baseline=muted/cinza; atual=ink; tokens DAY/NIGHT.
7. **Conclusão sustentada:** Mostra onde o modelo erra mais/menos entre grandes entidades efetivamente avaliadas.
8. **Limites e leituras incorretas:** B agrega rotas de cada companhia; não é erro por companhia×rota individual. Não representa entidades pequenas nem fatia de mercado; horizontes repetem targets.

## web-a-residuals — Residuals

1. **Localização:** `web/components/dashboard/ml-showcase.tsx` TaskView / Histogram.
2. **Modelo/experimento:** A.
3. **Objetivo:** Inspecionar assimetria, dispersão e caudas dos erros assinados.
4. **Eixos, unidade e legenda:** X: (predito−real)×100 em pp para B, ou (predito−real)/real para volumes. Y: número não ponderado de linhas; duas cores sobrepostas.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; residuals; 36,498 linhas incluídas de 36,500; bins fixos ±30 pp B ou ±100% volumes.
6. **Leitura estatística:** Positivo é sobreprevisão. Caudas são acumuladas no primeiro/último bin; p10/p50/p90 usam resíduos sem clipping. Lower is better; cor do modelo=chart-1/azul, baseline=muted/cinza; atual=ink; tokens DAY/NIGHT.
7. **Conclusão sustentada:** Sustenta descrição empírica de sinais e caudas na amostra incluída.
8. **Limites e leituras incorretas:** Volumes zero ficam fora do erro relativo; distribuição não ponderada pode discordar de WAPE/MAE ponderado. p10–p90 não é intervalo preditivo futuro.

## web-a-scatter — Actual vs predicted, row level

1. **Localização:** `web/components/dashboard/ml-showcase.tsx` TaskView / Scatter.
2. **Modelo/experimento:** A.
3. **Objetivo:** Ver alinhamento entre observações e predições pontuais.
4. **Eixos, unidade e legenda:** X: observado, Y: LightGBM, na unidade movements; diagonal y=x. Log nos dois eixos de volumes; linear para B.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; scatter: até 400 pares de validação h=1, amostra com seed 11; contém informação de linhas, embora limitada.
6. **Leitura estatística:** Abaixo da diagonal é subprevisão. Amostra é diagnóstica; score usa todas as linhas comparáveis. Lower is better; cor do modelo=chart-1/azul, baseline=muted/cinza; atual=ink; tokens DAY/NIGHT.
7. **Conclusão sustentada:** Sustenta o padrão visual de dispersão da amostra, sem estimar acurácia por densidade aparente.
8. **Limites e leituras incorretas:** Pares não positivos são removidos nos eixos log; pontos sobrepostos escondem densidade. Sem baseline ou intervalo de previsão por ponto.

## web-a-gain — What the trees split on

1. **Localização:** `web/components/dashboard/ml-showcase.tsx` TaskView / BarList.
2. **Modelo/experimento:** A.
3. **Objetivo:** Descrever como o booster de seleção distribuiu ganho de splits.
4. **Eixos, unidade e legenda:** Y: nome da feature; X/comprimento: fração do ganho total, exibida em %; top 10.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; top_features_by_gain dos reports/models; não recalculado do booster final refitado.
6. **Leitura estatística:** É importância interna do fitting, enviesável por cardinalidade e correlação. Lower is better; cor do modelo=chart-1/azul, baseline=muted/cinza; atual=ink; tokens DAY/NIGHT.
7. **Conclusão sustentada:** Permite verificar se o modelo usa níveis, calendário e identidades plausíveis.
8. **Limites e leituras incorretas:** Não é SHAP, efeito causal, contribuição de uma predição nem permutation importance em validação. Top 10 não soma necessariamente 100%.

## web-a-horizon-table — Error by horizon

1. **Localização:** `ml-showcase.tsx` / DataTable.
2. **Modelo/experimento:** A.
3. **Objetivo:** Comparar todas as regras e o viés em cada horizonte.
4. **Eixos, unidade e legenda:** Linhas: horizonte origem→target; colunas: WAPE, % de cada método e viés assinado.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; by_horizon. Viés B corrigido usa seat_weighted_bias_model; demais usam bias_model.
6. **Leitura estatística:** Selecionar o menor ponto não demonstra significância. Os CIs por horizonte estão em EXPERIMENT_RESULTS.
7. **Conclusão sustentada:** A e B h=1/h=3 não têm ganho conclusivo; D h=6 não demonstra superioridade.
8. **Limites e leituras incorretas:** A regra global pode mudar por horizonte. Tabela não segue o seletor do gráfico mensal.

## web-a-kpi-model — model KPI

1. **Localização:** `ml-showcase.tsx` / StatTile.
2. **Modelo/experimento:** A.
3. **Objetivo:** Erro do LightGBM no conjunto comparável.
4. **Eixos, unidade e legenda:** Sem eixos; número e unidade explícitos. CIs de erro quando exibidos.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`
6. **Leitura estatística:** Valores agregam horizontes e linhas comparáveis; não são métricas de teste.
7. **Conclusão sustentada:** A mantém baseline; B/D têm evidência histórica agregada, sujeita às ressalvas auditadas.
8. **Limites e leituras incorretas:** Um percentual de erro não é accuracy; a decisão histórica não valida o modelo corrigido futuro.

## web-a-kpi-baseline — baseline KPI

1. **Localização:** `ml-showcase.tsx` / StatTile.
2. **Modelo/experimento:** A.
3. **Objetivo:** Menor erro entre baselines no mesmo conjunto.
4. **Eixos, unidade e legenda:** Sem eixos; número e unidade explícitos. CIs de erro quando exibidos.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`
6. **Leitura estatística:** Valores agregam horizontes e linhas comparáveis; não são métricas de teste.
7. **Conclusão sustentada:** A mantém baseline; B/D têm evidência histórica agregada, sujeita às ressalvas auditadas.
8. **Limites e leituras incorretas:** Um percentual de erro não é accuracy; a decisão histórica não valida o modelo corrigido futuro.

## web-a-kpi-difference — difference KPI

1. **Localização:** `ml-showcase.tsx` / StatTile.
2. **Modelo/experimento:** A.
3. **Objetivo:** Erro modelo menos melhor baseline; diferença pareada.
4. **Eixos, unidade e legenda:** Sem eixos; número e unidade explícitos. CIs de erro quando exibidos.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`
6. **Leitura estatística:** Valores agregam horizontes e linhas comparáveis; não são métricas de teste.
7. **Conclusão sustentada:** A mantém baseline; B/D têm evidência histórica agregada, sujeita às ressalvas auditadas.
8. **Limites e leituras incorretas:** Um percentual de erro não é accuracy; a decisão histórica não valida o modelo corrigido futuro.

## web-a-kpi-bias — bias KPI

1. **Localização:** `ml-showcase.tsx` / StatTile.
2. **Modelo/experimento:** A.
3. **Objetivo:** Erro assinado; B ponderado por assentos em pp, volumes relativos em %.
4. **Eixos, unidade e legenda:** Sem eixos; número e unidade explícitos. CIs de erro quando exibidos.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`
6. **Leitura estatística:** Valores agregam horizontes e linhas comparáveis; não são métricas de teste.
7. **Conclusão sustentada:** A mantém baseline; B/D têm evidência histórica agregada, sujeita às ressalvas auditadas.
8. **Limites e leituras incorretas:** Um percentual de erro não é accuracy; a decisão histórica não valida o modelo corrigido futuro.

## web-a-examples — Retrospective hits and misses

1. **Localização:** `ml-showcase.tsx` / ExampleChart → LinesChart.
2. **Modelo/experimento:** A.
3. **Objetivo:** Inspecionar dois extremos escolhidos retrospectivamente, sem representar toda a população.
4. **Eixos, unidade e legenda:** X: dia de 2023 para A ou mês para D-pax. Y: movements; atual, modelo, regra.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; examples.best/worst. Seleção por erro agrupado entre top 10 aeroportos ou top 20 rotas; séries apenas h=1.
6. **Leitura estatística:** O score escrito pertence ao agrupamento de horizontes usado no ranking, não só à curva h=1.
7. **Conclusão sustentada:** Ilustra falhas/acertos concretos nas entidades escolhidas.
8. **Limites e leituras incorretas:** Cherry-picking descritivo explicitado; não é comparação prospectiva, teste de significância ou amostra representativa.

## paper-a_actual_vs_predicted_monthly — a_actual_vs_predicted_monthly

1. **Localização:** `research/ml-showcase/figures/a_actual_vs_predicted_monthly.png` (+ `.svg`).
2. **Modelo/experimento:** A.
3. **Objetivo:** Comparar nível observado, previsão de seleção e referência.
4. **Eixos, unidade e legenda:** X: janeiro a dezembro de 2023. Y: movements. Atual, LightGBM e melhor baseline global.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; monthly, filtrado por horizon; B usa assentos observados como pesos de todas as séries.
6. **Leitura estatística:** A proximidade de totais/médias avalia nível agregado, não igualdade por unidade.
7. **Conclusão sustentada:** Revela desvios temporais e de nível do experimento selecionado.
8. **Limites e leituras incorretas:** Cancelamentos de erro podem ocultar falhas de rota/dia. Só este gráfico acompanha o seletor de horizonte; comparação fixa no melhor baseline agregado. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-a_scatter — a_scatter

1. **Localização:** `research/ml-showcase/figures/a_scatter.png` (+ `.svg`).
2. **Modelo/experimento:** A.
3. **Objetivo:** Ver alinhamento entre observações e predições pontuais.
4. **Eixos, unidade e legenda:** X: observado, Y: LightGBM, na unidade movements; diagonal y=x. Log nos dois eixos de volumes; linear para B.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; scatter_sample com n≤4.000 e seed 7; distingue-se dos 400 pares seed 11 da web.
6. **Leitura estatística:** Abaixo da diagonal é subprevisão. Amostra é diagnóstica; score usa todas as linhas comparáveis.
7. **Conclusão sustentada:** Sustenta o padrão visual de dispersão da amostra, sem estimar acurácia por densidade aparente.
8. **Limites e leituras incorretas:** Pares não positivos são removidos nos eixos log; pontos sobrepostos escondem densidade. Sem baseline ou intervalo de previsão por ponto. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-a_residuals — a_residuals

1. **Localização:** `research/ml-showcase/figures/a_residuals.png` (+ `.svg`).
2. **Modelo/experimento:** A.
3. **Objetivo:** Inspecionar assimetria, dispersão e caudas dos erros assinados.
4. **Eixos, unidade e legenda:** X: (predito−real)×100 em pp para B, ou (predito−real)/real para volumes. Y: número não ponderado de linhas; duas cores sobrepostas.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; residuals; 36,498 linhas incluídas de 36,500; bins fixos ±30 pp B ou ±100% volumes.
6. **Leitura estatística:** Positivo é sobreprevisão. Caudas são acumuladas no primeiro/último bin; p10/p50/p90 usam resíduos sem clipping.
7. **Conclusão sustentada:** Sustenta descrição empírica de sinais e caudas na amostra incluída.
8. **Limites e leituras incorretas:** Volumes zero ficam fora do erro relativo; distribuição não ponderada pode discordar de WAPE/MAE ponderado. p10–p90 não é intervalo preditivo futuro. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-a_by_horizon — a_by_horizon

1. **Localização:** `research/ml-showcase/figures/a_by_horizon.png` (+ `.svg`).
2. **Modelo/experimento:** A.
3. **Objetivo:** Comparar erros por horizonte em barras agrupadas.
4. **Eixos, unidade e legenda:** X: h=1/3 ou 1/3/6; Y: WAPE, %; uma barra por método.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; by_horizon, todas as regras.
6. **Leitura estatística:** Mesmo conjunto de linhas por método; só estimativas pontuais no gráfico.
7. **Conclusão sustentada:** Revela heterogeneidade por horizonte, sem dispensar os intervalos pareados.
8. **Limites e leituras incorretas:** Não declarar superioridade apenas pelo menor comprimento; não há CI de diferença desenhado. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-a_by_volume — a_by_volume

1. **Localização:** `research/ml-showcase/figures/a_by_volume.png` (+ `.svg`).
2. **Modelo/experimento:** A.
3. **Objetivo:** Inspecionar heterogeneidade do erro por tamanho histórico.
4. **Eixos, unidade e legenda:** X: decis 1–10 da feature SIZE conhecida no cutoff. Y: WAPE, %, modelo e baseline.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; by_volume_decile; níveis A=hist_level_56, B=hist_seats_mean_12, D=hist_pax/seats_mean_12.
6. **Leitura estatística:** Agrupa observações por feature histórica; limites dos decis são estimados em 2023.
7. **Conclusão sustentada:** Sustenta diferenças descritivas de dificuldade entre estratos observados.
8. **Limites e leituras incorretas:** Não é WAPE por número de unidades nem ranking futuro. Decis não são limiares fixados no treino; os horizontes estão agrupados. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-a_by_entity — a_by_entity

1. **Localização:** `research/ml-showcase/figures/a_by_entity.png` (+ `.svg`).
2. **Modelo/experimento:** A.
3. **Objetivo:** Comparar modelo e regra nas maiores entidades observadas.
4. **Eixos, unidade e legenda:** Entidade no eixo categórico; comprimento horizontal= WAPE, %. Azul modelo, cinza baseline.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; by_entity: até 20 entidades, em vez das 10 da web.
6. **Leitura estatística:** Ranking é retrospectivo e os erros são recalculados sobre as linhas de cada entidade.
7. **Conclusão sustentada:** Mostra onde o modelo erra mais/menos entre grandes entidades efetivamente avaliadas.
8. **Limites e leituras incorretas:** B agrega rotas de cada companhia; não é erro por companhia×rota individual. Não representa entidades pequenas nem fatia de mercado; horizontes repetem targets. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-a_feature_gain — a_feature_gain

1. **Localização:** `research/ml-showcase/figures/a_feature_gain.png` (+ `.svg`).
2. **Modelo/experimento:** A.
3. **Objetivo:** Descrever como o booster de seleção distribuiu ganho de splits.
4. **Eixos, unidade e legenda:** Y: nome da feature; X/comprimento: fração do ganho total, exibida em %; top 10.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; top_features_by_gain dos reports/models; não recalculado do booster final refitado.
6. **Leitura estatística:** É importância interna do fitting, enviesável por cardinalidade e correlação.
7. **Conclusão sustentada:** Permite verificar se o modelo usa níveis, calendário e identidades plausíveis.
8. **Limites e leituras incorretas:** Não é SHAP, efeito causal, contribuição de uma predição nem permutation importance em validação. Top 10 não soma necessariamente 100%. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-a_error_by_month — a_error_by_month

1. **Localização:** `research/ml-showcase/figures/a_error_by_month.png` (+ `.svg`).
2. **Modelo/experimento:** A.
3. **Objetivo:** Examinar a variação do erro de unidade por target-month.
4. **Eixos, unidade e legenda:** X: mês de 2023; Y: WAPE, %. Painéis por horizonte, curvas modelo e baseline.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; monthly.model_error/baseline_error.
6. **Leitura estatística:** Erro calculado antes de agregar; não é erro entre os totais do gráfico de nível.
7. **Conclusão sustentada:** Mostra sazonalidade do desempenho no ano avaliado.
8. **Limites e leituras incorretas:** Doze pontos por horizonte não provam um padrão anual generalizável; compara a regra global. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-a_examples_daily — a_examples_daily

1. **Localização:** `research/ml-showcase/figures/a_examples_daily.png` (+ `.svg`).
2. **Modelo/experimento:** A.
3. **Objetivo:** Mesmos extremos da web em painéis estáticos.
4. **Eixos, unidade e legenda:** X: dia/mês de 2023, h=1; Y: movements. Três séries identificadas na legenda.
5. **Dados e proveniência:** `analysis.py::fig_examples_a/fig_examples_routes`, seleção retrospectiva pelos erros agrupados.
6. **Leitura estatística:** Título histórico associa WAPE agrupado a uma curva h=1: a distinção é obrigatória nesta leitura.
7. **Conclusão sustentada:** Permite inspecionar visualmente entidades escolhidas após a avaliação.
8. **Limites e leituras incorretas:** Casos extremos não são representativos. Figuras históricas mantidas; errata documenta o escopo do score.

## web-b-monthly — Actual vs predicted, by target month

1. **Localização:** `web/components/dashboard/ml-showcase.tsx` TaskView / LinesChart.
2. **Modelo/experimento:** B.
3. **Objetivo:** Comparar nível observado, previsão de seleção e referência.
4. **Eixos, unidade e legenda:** X: janeiro a dezembro de 2023. Y: ocupação paga, fração exibida em %. Atual, LightGBM e melhor baseline global.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; monthly, filtrado por horizon; B usa assentos observados como pesos de todas as séries.
6. **Leitura estatística:** A proximidade de totais/médias avalia nível agregado, não igualdade por unidade. Lower is better; cor do modelo=chart-1/azul, baseline=muted/cinza; atual=ink; tokens DAY/NIGHT.
7. **Conclusão sustentada:** Revela desvios temporais e de nível do experimento selecionado.
8. **Limites e leituras incorretas:** Cancelamentos de erro podem ocultar falhas de rota/dia. Só este gráfico acompanha o seletor de horizonte; comparação fixa no melhor baseline agregado.

## web-b-volume — Error by traffic volume

1. **Localização:** `web/components/dashboard/ml-showcase.tsx` TaskView / LinesChart.
2. **Modelo/experimento:** B.
3. **Objetivo:** Inspecionar heterogeneidade do erro por tamanho histórico.
4. **Eixos, unidade e legenda:** X: decis 1–10 da feature SIZE conhecida no cutoff. Y: MAE ponderado por assentos, pp, modelo e baseline.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; by_volume_decile; níveis A=hist_level_56, B=hist_seats_mean_12, D=hist_pax/seats_mean_12.
6. **Leitura estatística:** Agrupa observações por feature histórica; limites dos decis são estimados em 2023. Lower is better; cor do modelo=chart-1/azul, baseline=muted/cinza; atual=ink; tokens DAY/NIGHT.
7. **Conclusão sustentada:** Sustenta diferenças descritivas de dificuldade entre estratos observados.
8. **Limites e leituras incorretas:** Não é WAPE por número de unidades nem ranking futuro. Decis não são limiares fixados no treino; os horizontes estão agrupados.

## web-b-entity — Largest units, by carrier

1. **Localização:** `web/components/dashboard/ml-showcase.tsx` TaskView / PairBars.
2. **Modelo/experimento:** B.
3. **Objetivo:** Comparar modelo e regra nas maiores entidades observadas.
4. **Eixos, unidade e legenda:** Entidade no eixo categórico; comprimento horizontal= MAE ponderado por assentos, pp. Azul modelo, cinza baseline.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; by_entity[:10], agrupado por aeroporto A, companhia B ou rota D; tamanho por volume observado em 2023.
6. **Leitura estatística:** Ranking é retrospectivo e os erros são recalculados sobre as linhas de cada entidade. Lower is better; cor do modelo=chart-1/azul, baseline=muted/cinza; atual=ink; tokens DAY/NIGHT.
7. **Conclusão sustentada:** Mostra onde o modelo erra mais/menos entre grandes entidades efetivamente avaliadas.
8. **Limites e leituras incorretas:** B agrega rotas de cada companhia; não é erro por companhia×rota individual. Não representa entidades pequenas nem fatia de mercado; horizontes repetem targets.

## web-b-residuals — Residuals

1. **Localização:** `web/components/dashboard/ml-showcase.tsx` TaskView / Histogram.
2. **Modelo/experimento:** B.
3. **Objetivo:** Inspecionar assimetria, dispersão e caudas dos erros assinados.
4. **Eixos, unidade e legenda:** X: (predito−real)×100 em pp para B, ou (predito−real)/real para volumes. Y: número não ponderado de linhas; duas cores sobrepostas.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; residuals; 42,369 linhas incluídas de 42,369; bins fixos ±30 pp B ou ±100% volumes.
6. **Leitura estatística:** Positivo é sobreprevisão. Caudas são acumuladas no primeiro/último bin; p10/p50/p90 usam resíduos sem clipping. Lower is better; cor do modelo=chart-1/azul, baseline=muted/cinza; atual=ink; tokens DAY/NIGHT.
7. **Conclusão sustentada:** Sustenta descrição empírica de sinais e caudas na amostra incluída.
8. **Limites e leituras incorretas:** Volumes zero ficam fora do erro relativo; distribuição não ponderada pode discordar de WAPE/MAE ponderado. p10–p90 não é intervalo preditivo futuro.

## web-b-scatter — Actual vs predicted, row level

1. **Localização:** `web/components/dashboard/ml-showcase.tsx` TaskView / Scatter.
2. **Modelo/experimento:** B.
3. **Objetivo:** Ver alinhamento entre observações e predições pontuais.
4. **Eixos, unidade e legenda:** X: observado, Y: LightGBM, na unidade ocupação paga, fração exibida em %; diagonal y=x. Log nos dois eixos de volumes; linear para B.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; scatter: até 400 pares de validação h=1, amostra com seed 11; contém informação de linhas, embora limitada.
6. **Leitura estatística:** Abaixo da diagonal é subprevisão. Amostra é diagnóstica; score usa todas as linhas comparáveis. Lower is better; cor do modelo=chart-1/azul, baseline=muted/cinza; atual=ink; tokens DAY/NIGHT.
7. **Conclusão sustentada:** Sustenta o padrão visual de dispersão da amostra, sem estimar acurácia por densidade aparente.
8. **Limites e leituras incorretas:** Pares não positivos são removidos nos eixos log; pontos sobrepostos escondem densidade. Sem baseline ou intervalo de previsão por ponto.

## web-b-gain — What the trees split on

1. **Localização:** `web/components/dashboard/ml-showcase.tsx` TaskView / BarList.
2. **Modelo/experimento:** B.
3. **Objetivo:** Descrever como o booster de seleção distribuiu ganho de splits.
4. **Eixos, unidade e legenda:** Y: nome da feature; X/comprimento: fração do ganho total, exibida em %; top 10.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; top_features_by_gain dos reports/models; não recalculado do booster final refitado.
6. **Leitura estatística:** É importância interna do fitting, enviesável por cardinalidade e correlação. Lower is better; cor do modelo=chart-1/azul, baseline=muted/cinza; atual=ink; tokens DAY/NIGHT.
7. **Conclusão sustentada:** Permite verificar se o modelo usa níveis, calendário e identidades plausíveis.
8. **Limites e leituras incorretas:** Não é SHAP, efeito causal, contribuição de uma predição nem permutation importance em validação. Top 10 não soma necessariamente 100%.

## web-b-horizon-table — Error by horizon

1. **Localização:** `ml-showcase.tsx` / DataTable.
2. **Modelo/experimento:** B.
3. **Objetivo:** Comparar todas as regras e o viés em cada horizonte.
4. **Eixos, unidade e legenda:** Linhas: horizonte origem→target; colunas: MAE ponderado por assentos, pp de cada método e viés assinado.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; by_horizon. Viés B corrigido usa seat_weighted_bias_model; demais usam bias_model.
6. **Leitura estatística:** Selecionar o menor ponto não demonstra significância. Os CIs por horizonte estão em EXPERIMENT_RESULTS.
7. **Conclusão sustentada:** A e B h=1/h=3 não têm ganho conclusivo; D h=6 não demonstra superioridade.
8. **Limites e leituras incorretas:** A regra global pode mudar por horizonte. Tabela não segue o seletor do gráfico mensal.

## web-b-kpi-model — model KPI

1. **Localização:** `ml-showcase.tsx` / StatTile.
2. **Modelo/experimento:** B.
3. **Objetivo:** Erro do LightGBM no conjunto comparável.
4. **Eixos, unidade e legenda:** Sem eixos; número e unidade explícitos. CIs de erro quando exibidos.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`
6. **Leitura estatística:** Valores agregam horizontes e linhas comparáveis; não são métricas de teste.
7. **Conclusão sustentada:** A mantém baseline; B/D têm evidência histórica agregada, sujeita às ressalvas auditadas.
8. **Limites e leituras incorretas:** Um percentual de erro não é accuracy; a decisão histórica não valida o modelo corrigido futuro.

## web-b-kpi-baseline — baseline KPI

1. **Localização:** `ml-showcase.tsx` / StatTile.
2. **Modelo/experimento:** B.
3. **Objetivo:** Menor erro entre baselines no mesmo conjunto.
4. **Eixos, unidade e legenda:** Sem eixos; número e unidade explícitos. CIs de erro quando exibidos.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`
6. **Leitura estatística:** Valores agregam horizontes e linhas comparáveis; não são métricas de teste.
7. **Conclusão sustentada:** A mantém baseline; B/D têm evidência histórica agregada, sujeita às ressalvas auditadas.
8. **Limites e leituras incorretas:** Um percentual de erro não é accuracy; a decisão histórica não valida o modelo corrigido futuro.

## web-b-kpi-difference — difference KPI

1. **Localização:** `ml-showcase.tsx` / StatTile.
2. **Modelo/experimento:** B.
3. **Objetivo:** Erro modelo menos melhor baseline; diferença pareada.
4. **Eixos, unidade e legenda:** Sem eixos; número e unidade explícitos. CIs de erro quando exibidos.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`
6. **Leitura estatística:** Valores agregam horizontes e linhas comparáveis; não são métricas de teste.
7. **Conclusão sustentada:** A mantém baseline; B/D têm evidência histórica agregada, sujeita às ressalvas auditadas.
8. **Limites e leituras incorretas:** Um percentual de erro não é accuracy; a decisão histórica não valida o modelo corrigido futuro.

## web-b-kpi-bias — bias KPI

1. **Localização:** `ml-showcase.tsx` / StatTile.
2. **Modelo/experimento:** B.
3. **Objetivo:** Erro assinado; B ponderado por assentos em pp, volumes relativos em %.
4. **Eixos, unidade e legenda:** Sem eixos; número e unidade explícitos. CIs de erro quando exibidos.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`
6. **Leitura estatística:** Valores agregam horizontes e linhas comparáveis; não são métricas de teste.
7. **Conclusão sustentada:** A mantém baseline; B/D têm evidência histórica agregada, sujeita às ressalvas auditadas.
8. **Limites e leituras incorretas:** Um percentual de erro não é accuracy; a decisão histórica não valida o modelo corrigido futuro.

## paper-b_actual_vs_predicted_monthly — b_actual_vs_predicted_monthly

1. **Localização:** `research/ml-showcase/figures/b_actual_vs_predicted_monthly.png` (+ `.svg`).
2. **Modelo/experimento:** B.
3. **Objetivo:** Comparar nível observado, previsão de seleção e referência.
4. **Eixos, unidade e legenda:** X: janeiro a dezembro de 2023. Y: ocupação paga, fração exibida em %. Atual, LightGBM e melhor baseline global.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; monthly, filtrado por horizon; B usa assentos observados como pesos de todas as séries.
6. **Leitura estatística:** A proximidade de totais/médias avalia nível agregado, não igualdade por unidade.
7. **Conclusão sustentada:** Revela desvios temporais e de nível do experimento selecionado.
8. **Limites e leituras incorretas:** Cancelamentos de erro podem ocultar falhas de rota/dia. Só este gráfico acompanha o seletor de horizonte; comparação fixa no melhor baseline agregado. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-b_scatter — b_scatter

1. **Localização:** `research/ml-showcase/figures/b_scatter.png` (+ `.svg`).
2. **Modelo/experimento:** B.
3. **Objetivo:** Ver alinhamento entre observações e predições pontuais.
4. **Eixos, unidade e legenda:** X: observado, Y: LightGBM, na unidade ocupação paga, fração exibida em %; diagonal y=x. Log nos dois eixos de volumes; linear para B.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; scatter_sample com n≤4.000 e seed 7; distingue-se dos 400 pares seed 11 da web.
6. **Leitura estatística:** Abaixo da diagonal é subprevisão. Amostra é diagnóstica; score usa todas as linhas comparáveis.
7. **Conclusão sustentada:** Sustenta o padrão visual de dispersão da amostra, sem estimar acurácia por densidade aparente.
8. **Limites e leituras incorretas:** Pares não positivos são removidos nos eixos log; pontos sobrepostos escondem densidade. Sem baseline ou intervalo de previsão por ponto. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-b_residuals — b_residuals

1. **Localização:** `research/ml-showcase/figures/b_residuals.png` (+ `.svg`).
2. **Modelo/experimento:** B.
3. **Objetivo:** Inspecionar assimetria, dispersão e caudas dos erros assinados.
4. **Eixos, unidade e legenda:** X: (predito−real)×100 em pp para B, ou (predito−real)/real para volumes. Y: número não ponderado de linhas; duas cores sobrepostas.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; residuals; 42,369 linhas incluídas de 42,369; bins fixos ±30 pp B ou ±100% volumes.
6. **Leitura estatística:** Positivo é sobreprevisão. Caudas são acumuladas no primeiro/último bin; p10/p50/p90 usam resíduos sem clipping.
7. **Conclusão sustentada:** Sustenta descrição empírica de sinais e caudas na amostra incluída.
8. **Limites e leituras incorretas:** Volumes zero ficam fora do erro relativo; distribuição não ponderada pode discordar de WAPE/MAE ponderado. p10–p90 não é intervalo preditivo futuro. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-b_by_horizon — b_by_horizon

1. **Localização:** `research/ml-showcase/figures/b_by_horizon.png` (+ `.svg`).
2. **Modelo/experimento:** B.
3. **Objetivo:** Comparar erros por horizonte em barras agrupadas.
4. **Eixos, unidade e legenda:** X: h=1/3 ou 1/3/6; Y: MAE ponderado por assentos, pp; uma barra por método.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; by_horizon, todas as regras.
6. **Leitura estatística:** Mesmo conjunto de linhas por método; só estimativas pontuais no gráfico.
7. **Conclusão sustentada:** Revela heterogeneidade por horizonte, sem dispensar os intervalos pareados.
8. **Limites e leituras incorretas:** Não declarar superioridade apenas pelo menor comprimento; não há CI de diferença desenhado. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-b_by_volume — b_by_volume

1. **Localização:** `research/ml-showcase/figures/b_by_volume.png` (+ `.svg`).
2. **Modelo/experimento:** B.
3. **Objetivo:** Inspecionar heterogeneidade do erro por tamanho histórico.
4. **Eixos, unidade e legenda:** X: decis 1–10 da feature SIZE conhecida no cutoff. Y: MAE ponderado por assentos, pp, modelo e baseline.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; by_volume_decile; níveis A=hist_level_56, B=hist_seats_mean_12, D=hist_pax/seats_mean_12.
6. **Leitura estatística:** Agrupa observações por feature histórica; limites dos decis são estimados em 2023.
7. **Conclusão sustentada:** Sustenta diferenças descritivas de dificuldade entre estratos observados.
8. **Limites e leituras incorretas:** Não é WAPE por número de unidades nem ranking futuro. Decis não são limiares fixados no treino; os horizontes estão agrupados. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-b_by_entity — b_by_entity

1. **Localização:** `research/ml-showcase/figures/b_by_entity.png` (+ `.svg`).
2. **Modelo/experimento:** B.
3. **Objetivo:** Comparar modelo e regra nas maiores entidades observadas.
4. **Eixos, unidade e legenda:** Entidade no eixo categórico; comprimento horizontal= MAE ponderado por assentos, pp. Azul modelo, cinza baseline.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; by_entity: até 20 entidades, em vez das 10 da web.
6. **Leitura estatística:** Ranking é retrospectivo e os erros são recalculados sobre as linhas de cada entidade.
7. **Conclusão sustentada:** Mostra onde o modelo erra mais/menos entre grandes entidades efetivamente avaliadas.
8. **Limites e leituras incorretas:** B agrega rotas de cada companhia; não é erro por companhia×rota individual. Não representa entidades pequenas nem fatia de mercado; horizontes repetem targets. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-b_feature_gain — b_feature_gain

1. **Localização:** `research/ml-showcase/figures/b_feature_gain.png` (+ `.svg`).
2. **Modelo/experimento:** B.
3. **Objetivo:** Descrever como o booster de seleção distribuiu ganho de splits.
4. **Eixos, unidade e legenda:** Y: nome da feature; X/comprimento: fração do ganho total, exibida em %; top 10.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; top_features_by_gain dos reports/models; não recalculado do booster final refitado.
6. **Leitura estatística:** É importância interna do fitting, enviesável por cardinalidade e correlação.
7. **Conclusão sustentada:** Permite verificar se o modelo usa níveis, calendário e identidades plausíveis.
8. **Limites e leituras incorretas:** Não é SHAP, efeito causal, contribuição de uma predição nem permutation importance em validação. Top 10 não soma necessariamente 100%. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-b_error_by_month — b_error_by_month

1. **Localização:** `research/ml-showcase/figures/b_error_by_month.png` (+ `.svg`).
2. **Modelo/experimento:** B.
3. **Objetivo:** Examinar a variação do erro de unidade por target-month.
4. **Eixos, unidade e legenda:** X: mês de 2023; Y: MAE ponderado por assentos, pp. Painéis por horizonte, curvas modelo e baseline.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; monthly.model_error/baseline_error.
6. **Leitura estatística:** Erro calculado antes de agregar; não é erro entre os totais do gráfico de nível.
7. **Conclusão sustentada:** Mostra sazonalidade do desempenho no ano avaliado.
8. **Limites e leituras incorretas:** Doze pontos por horizonte não provam um padrão anual generalizável; compara a regra global. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## web-d_pax-monthly — Actual vs predicted, by target month

1. **Localização:** `web/components/dashboard/ml-showcase.tsx` TaskView / LinesChart.
2. **Modelo/experimento:** D-pax.
3. **Objetivo:** Comparar nível observado, previsão de seleção e referência.
4. **Eixos, unidade e legenda:** X: janeiro a dezembro de 2023. Y: paid passengers. Atual, LightGBM e melhor baseline global.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; monthly, filtrado por horizon; B usa assentos observados como pesos de todas as séries.
6. **Leitura estatística:** A proximidade de totais/médias avalia nível agregado, não igualdade por unidade. Lower is better; cor do modelo=chart-1/azul, baseline=muted/cinza; atual=ink; tokens DAY/NIGHT.
7. **Conclusão sustentada:** Revela desvios temporais e de nível do experimento selecionado.
8. **Limites e leituras incorretas:** Cancelamentos de erro podem ocultar falhas de rota/dia. Só este gráfico acompanha o seletor de horizonte; comparação fixa no melhor baseline agregado.

## web-d_pax-volume — Error by traffic volume

1. **Localização:** `web/components/dashboard/ml-showcase.tsx` TaskView / LinesChart.
2. **Modelo/experimento:** D-pax.
3. **Objetivo:** Inspecionar heterogeneidade do erro por tamanho histórico.
4. **Eixos, unidade e legenda:** X: decis 1–10 da feature SIZE conhecida no cutoff. Y: WAPE, %, modelo e baseline.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; by_volume_decile; níveis A=hist_level_56, B=hist_seats_mean_12, D=hist_pax/seats_mean_12.
6. **Leitura estatística:** Agrupa observações por feature histórica; limites dos decis são estimados em 2023. Lower is better; cor do modelo=chart-1/azul, baseline=muted/cinza; atual=ink; tokens DAY/NIGHT.
7. **Conclusão sustentada:** Sustenta diferenças descritivas de dificuldade entre estratos observados.
8. **Limites e leituras incorretas:** Não é WAPE por número de unidades nem ranking futuro. Decis não são limiares fixados no treino; os horizontes estão agrupados.

## web-d_pax-entity — Largest units, by directed route

1. **Localização:** `web/components/dashboard/ml-showcase.tsx` TaskView / PairBars.
2. **Modelo/experimento:** D-pax.
3. **Objetivo:** Comparar modelo e regra nas maiores entidades observadas.
4. **Eixos, unidade e legenda:** Entidade no eixo categórico; comprimento horizontal= WAPE, %. Azul modelo, cinza baseline.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; by_entity[:10], agrupado por aeroporto A, companhia B ou rota D; tamanho por volume observado em 2023.
6. **Leitura estatística:** Ranking é retrospectivo e os erros são recalculados sobre as linhas de cada entidade. Lower is better; cor do modelo=chart-1/azul, baseline=muted/cinza; atual=ink; tokens DAY/NIGHT.
7. **Conclusão sustentada:** Mostra onde o modelo erra mais/menos entre grandes entidades efetivamente avaliadas.
8. **Limites e leituras incorretas:** B agrega rotas de cada companhia; não é erro por companhia×rota individual. Não representa entidades pequenas nem fatia de mercado; horizontes repetem targets.

## web-d_pax-residuals — Residuals

1. **Localização:** `web/components/dashboard/ml-showcase.tsx` TaskView / Histogram.
2. **Modelo/experimento:** D-pax.
3. **Objetivo:** Inspecionar assimetria, dispersão e caudas dos erros assinados.
4. **Eixos, unidade e legenda:** X: (predito−real)×100 em pp para B, ou (predito−real)/real para volumes. Y: número não ponderado de linhas; duas cores sobrepostas.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; residuals; 31,465 linhas incluídas de 33,762; bins fixos ±30 pp B ou ±100% volumes.
6. **Leitura estatística:** Positivo é sobreprevisão. Caudas são acumuladas no primeiro/último bin; p10/p50/p90 usam resíduos sem clipping. Lower is better; cor do modelo=chart-1/azul, baseline=muted/cinza; atual=ink; tokens DAY/NIGHT.
7. **Conclusão sustentada:** Sustenta descrição empírica de sinais e caudas na amostra incluída.
8. **Limites e leituras incorretas:** Volumes zero ficam fora do erro relativo; distribuição não ponderada pode discordar de WAPE/MAE ponderado. p10–p90 não é intervalo preditivo futuro.

## web-d_pax-scatter — Actual vs predicted, row level

1. **Localização:** `web/components/dashboard/ml-showcase.tsx` TaskView / Scatter.
2. **Modelo/experimento:** D-pax.
3. **Objetivo:** Ver alinhamento entre observações e predições pontuais.
4. **Eixos, unidade e legenda:** X: observado, Y: LightGBM, na unidade paid passengers; diagonal y=x. Log nos dois eixos de volumes; linear para B.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; scatter: até 400 pares de validação h=1, amostra com seed 11; contém informação de linhas, embora limitada.
6. **Leitura estatística:** Abaixo da diagonal é subprevisão. Amostra é diagnóstica; score usa todas as linhas comparáveis. Lower is better; cor do modelo=chart-1/azul, baseline=muted/cinza; atual=ink; tokens DAY/NIGHT.
7. **Conclusão sustentada:** Sustenta o padrão visual de dispersão da amostra, sem estimar acurácia por densidade aparente.
8. **Limites e leituras incorretas:** Pares não positivos são removidos nos eixos log; pontos sobrepostos escondem densidade. Sem baseline ou intervalo de previsão por ponto.

## web-d_pax-gain — What the trees split on

1. **Localização:** `web/components/dashboard/ml-showcase.tsx` TaskView / BarList.
2. **Modelo/experimento:** D-pax.
3. **Objetivo:** Descrever como o booster de seleção distribuiu ganho de splits.
4. **Eixos, unidade e legenda:** Y: nome da feature; X/comprimento: fração do ganho total, exibida em %; top 10.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; top_features_by_gain dos reports/models; não recalculado do booster final refitado.
6. **Leitura estatística:** É importância interna do fitting, enviesável por cardinalidade e correlação. Lower is better; cor do modelo=chart-1/azul, baseline=muted/cinza; atual=ink; tokens DAY/NIGHT.
7. **Conclusão sustentada:** Permite verificar se o modelo usa níveis, calendário e identidades plausíveis.
8. **Limites e leituras incorretas:** Não é SHAP, efeito causal, contribuição de uma predição nem permutation importance em validação. Top 10 não soma necessariamente 100%.

## web-d_pax-horizon-table — Error by horizon

1. **Localização:** `ml-showcase.tsx` / DataTable.
2. **Modelo/experimento:** D-pax.
3. **Objetivo:** Comparar todas as regras e o viés em cada horizonte.
4. **Eixos, unidade e legenda:** Linhas: horizonte origem→target; colunas: WAPE, % de cada método e viés assinado.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; by_horizon. Viés B corrigido usa seat_weighted_bias_model; demais usam bias_model.
6. **Leitura estatística:** Selecionar o menor ponto não demonstra significância. Os CIs por horizonte estão em EXPERIMENT_RESULTS.
7. **Conclusão sustentada:** A e B h=1/h=3 não têm ganho conclusivo; D h=6 não demonstra superioridade.
8. **Limites e leituras incorretas:** A regra global pode mudar por horizonte. Tabela não segue o seletor do gráfico mensal.

## web-d_pax-kpi-model — model KPI

1. **Localização:** `ml-showcase.tsx` / StatTile.
2. **Modelo/experimento:** D-pax.
3. **Objetivo:** Erro do LightGBM no conjunto comparável.
4. **Eixos, unidade e legenda:** Sem eixos; número e unidade explícitos. CIs de erro quando exibidos.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`
6. **Leitura estatística:** Valores agregam horizontes e linhas comparáveis; não são métricas de teste.
7. **Conclusão sustentada:** A mantém baseline; B/D têm evidência histórica agregada, sujeita às ressalvas auditadas.
8. **Limites e leituras incorretas:** Um percentual de erro não é accuracy; a decisão histórica não valida o modelo corrigido futuro.

## web-d_pax-kpi-baseline — baseline KPI

1. **Localização:** `ml-showcase.tsx` / StatTile.
2. **Modelo/experimento:** D-pax.
3. **Objetivo:** Menor erro entre baselines no mesmo conjunto.
4. **Eixos, unidade e legenda:** Sem eixos; número e unidade explícitos. CIs de erro quando exibidos.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`
6. **Leitura estatística:** Valores agregam horizontes e linhas comparáveis; não são métricas de teste.
7. **Conclusão sustentada:** A mantém baseline; B/D têm evidência histórica agregada, sujeita às ressalvas auditadas.
8. **Limites e leituras incorretas:** Um percentual de erro não é accuracy; a decisão histórica não valida o modelo corrigido futuro.

## web-d_pax-kpi-difference — difference KPI

1. **Localização:** `ml-showcase.tsx` / StatTile.
2. **Modelo/experimento:** D-pax.
3. **Objetivo:** Erro modelo menos melhor baseline; diferença pareada.
4. **Eixos, unidade e legenda:** Sem eixos; número e unidade explícitos. CIs de erro quando exibidos.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`
6. **Leitura estatística:** Valores agregam horizontes e linhas comparáveis; não são métricas de teste.
7. **Conclusão sustentada:** A mantém baseline; B/D têm evidência histórica agregada, sujeita às ressalvas auditadas.
8. **Limites e leituras incorretas:** Um percentual de erro não é accuracy; a decisão histórica não valida o modelo corrigido futuro.

## web-d_pax-kpi-bias — bias KPI

1. **Localização:** `ml-showcase.tsx` / StatTile.
2. **Modelo/experimento:** D-pax.
3. **Objetivo:** Erro assinado; B ponderado por assentos em pp, volumes relativos em %.
4. **Eixos, unidade e legenda:** Sem eixos; número e unidade explícitos. CIs de erro quando exibidos.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`
6. **Leitura estatística:** Valores agregam horizontes e linhas comparáveis; não são métricas de teste.
7. **Conclusão sustentada:** A mantém baseline; B/D têm evidência histórica agregada, sujeita às ressalvas auditadas.
8. **Limites e leituras incorretas:** Um percentual de erro não é accuracy; a decisão histórica não valida o modelo corrigido futuro.

## web-d_pax-examples — Retrospective hits and misses

1. **Localização:** `ml-showcase.tsx` / ExampleChart → LinesChart.
2. **Modelo/experimento:** D-pax.
3. **Objetivo:** Inspecionar dois extremos escolhidos retrospectivamente, sem representar toda a população.
4. **Eixos, unidade e legenda:** X: dia de 2023 para A ou mês para D-pax. Y: paid passengers; atual, modelo, regra.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; examples.best/worst. Seleção por erro agrupado entre top 10 aeroportos ou top 20 rotas; séries apenas h=1.
6. **Leitura estatística:** O score escrito pertence ao agrupamento de horizontes usado no ranking, não só à curva h=1.
7. **Conclusão sustentada:** Ilustra falhas/acertos concretos nas entidades escolhidas.
8. **Limites e leituras incorretas:** Cherry-picking descritivo explicitado; não é comparação prospectiva, teste de significância ou amostra representativa.

## paper-d_pax_actual_vs_predicted_monthly — d_pax_actual_vs_predicted_monthly

1. **Localização:** `research/ml-showcase/figures/d_pax_actual_vs_predicted_monthly.png` (+ `.svg`).
2. **Modelo/experimento:** D-pax.
3. **Objetivo:** Comparar nível observado, previsão de seleção e referência.
4. **Eixos, unidade e legenda:** X: janeiro a dezembro de 2023. Y: paid passengers. Atual, LightGBM e melhor baseline global.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; monthly, filtrado por horizon; B usa assentos observados como pesos de todas as séries.
6. **Leitura estatística:** A proximidade de totais/médias avalia nível agregado, não igualdade por unidade.
7. **Conclusão sustentada:** Revela desvios temporais e de nível do experimento selecionado.
8. **Limites e leituras incorretas:** Cancelamentos de erro podem ocultar falhas de rota/dia. Só este gráfico acompanha o seletor de horizonte; comparação fixa no melhor baseline agregado. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-d_pax_scatter — d_pax_scatter

1. **Localização:** `research/ml-showcase/figures/d_pax_scatter.png` (+ `.svg`).
2. **Modelo/experimento:** D-pax.
3. **Objetivo:** Ver alinhamento entre observações e predições pontuais.
4. **Eixos, unidade e legenda:** X: observado, Y: LightGBM, na unidade paid passengers; diagonal y=x. Log nos dois eixos de volumes; linear para B.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; scatter_sample com n≤4.000 e seed 7; distingue-se dos 400 pares seed 11 da web.
6. **Leitura estatística:** Abaixo da diagonal é subprevisão. Amostra é diagnóstica; score usa todas as linhas comparáveis.
7. **Conclusão sustentada:** Sustenta o padrão visual de dispersão da amostra, sem estimar acurácia por densidade aparente.
8. **Limites e leituras incorretas:** Pares não positivos são removidos nos eixos log; pontos sobrepostos escondem densidade. Sem baseline ou intervalo de previsão por ponto. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-d_pax_residuals — d_pax_residuals

1. **Localização:** `research/ml-showcase/figures/d_pax_residuals.png` (+ `.svg`).
2. **Modelo/experimento:** D-pax.
3. **Objetivo:** Inspecionar assimetria, dispersão e caudas dos erros assinados.
4. **Eixos, unidade e legenda:** X: (predito−real)×100 em pp para B, ou (predito−real)/real para volumes. Y: número não ponderado de linhas; duas cores sobrepostas.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; residuals; 31,465 linhas incluídas de 33,762; bins fixos ±30 pp B ou ±100% volumes.
6. **Leitura estatística:** Positivo é sobreprevisão. Caudas são acumuladas no primeiro/último bin; p10/p50/p90 usam resíduos sem clipping.
7. **Conclusão sustentada:** Sustenta descrição empírica de sinais e caudas na amostra incluída.
8. **Limites e leituras incorretas:** Volumes zero ficam fora do erro relativo; distribuição não ponderada pode discordar de WAPE/MAE ponderado. p10–p90 não é intervalo preditivo futuro. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-d_pax_by_horizon — d_pax_by_horizon

1. **Localização:** `research/ml-showcase/figures/d_pax_by_horizon.png` (+ `.svg`).
2. **Modelo/experimento:** D-pax.
3. **Objetivo:** Comparar erros por horizonte em barras agrupadas.
4. **Eixos, unidade e legenda:** X: h=1/3 ou 1/3/6; Y: WAPE, %; uma barra por método.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; by_horizon, todas as regras.
6. **Leitura estatística:** Mesmo conjunto de linhas por método; só estimativas pontuais no gráfico.
7. **Conclusão sustentada:** Revela heterogeneidade por horizonte, sem dispensar os intervalos pareados.
8. **Limites e leituras incorretas:** Não declarar superioridade apenas pelo menor comprimento; não há CI de diferença desenhado. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-d_pax_by_volume — d_pax_by_volume

1. **Localização:** `research/ml-showcase/figures/d_pax_by_volume.png` (+ `.svg`).
2. **Modelo/experimento:** D-pax.
3. **Objetivo:** Inspecionar heterogeneidade do erro por tamanho histórico.
4. **Eixos, unidade e legenda:** X: decis 1–10 da feature SIZE conhecida no cutoff. Y: WAPE, %, modelo e baseline.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; by_volume_decile; níveis A=hist_level_56, B=hist_seats_mean_12, D=hist_pax/seats_mean_12.
6. **Leitura estatística:** Agrupa observações por feature histórica; limites dos decis são estimados em 2023.
7. **Conclusão sustentada:** Sustenta diferenças descritivas de dificuldade entre estratos observados.
8. **Limites e leituras incorretas:** Não é WAPE por número de unidades nem ranking futuro. Decis não são limiares fixados no treino; os horizontes estão agrupados. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-d_pax_by_entity — d_pax_by_entity

1. **Localização:** `research/ml-showcase/figures/d_pax_by_entity.png` (+ `.svg`).
2. **Modelo/experimento:** D-pax.
3. **Objetivo:** Comparar modelo e regra nas maiores entidades observadas.
4. **Eixos, unidade e legenda:** Entidade no eixo categórico; comprimento horizontal= WAPE, %. Azul modelo, cinza baseline.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; by_entity: até 20 entidades, em vez das 10 da web.
6. **Leitura estatística:** Ranking é retrospectivo e os erros são recalculados sobre as linhas de cada entidade.
7. **Conclusão sustentada:** Mostra onde o modelo erra mais/menos entre grandes entidades efetivamente avaliadas.
8. **Limites e leituras incorretas:** B agrega rotas de cada companhia; não é erro por companhia×rota individual. Não representa entidades pequenas nem fatia de mercado; horizontes repetem targets. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-d_pax_feature_gain — d_pax_feature_gain

1. **Localização:** `research/ml-showcase/figures/d_pax_feature_gain.png` (+ `.svg`).
2. **Modelo/experimento:** D-pax.
3. **Objetivo:** Descrever como o booster de seleção distribuiu ganho de splits.
4. **Eixos, unidade e legenda:** Y: nome da feature; X/comprimento: fração do ganho total, exibida em %; top 10.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; top_features_by_gain dos reports/models; não recalculado do booster final refitado.
6. **Leitura estatística:** É importância interna do fitting, enviesável por cardinalidade e correlação.
7. **Conclusão sustentada:** Permite verificar se o modelo usa níveis, calendário e identidades plausíveis.
8. **Limites e leituras incorretas:** Não é SHAP, efeito causal, contribuição de uma predição nem permutation importance em validação. Top 10 não soma necessariamente 100%. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-d_pax_error_by_month — d_pax_error_by_month

1. **Localização:** `research/ml-showcase/figures/d_pax_error_by_month.png` (+ `.svg`).
2. **Modelo/experimento:** D-pax.
3. **Objetivo:** Examinar a variação do erro de unidade por target-month.
4. **Eixos, unidade e legenda:** X: mês de 2023; Y: WAPE, %. Painéis por horizonte, curvas modelo e baseline.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; monthly.model_error/baseline_error.
6. **Leitura estatística:** Erro calculado antes de agregar; não é erro entre os totais do gráfico de nível.
7. **Conclusão sustentada:** Mostra sazonalidade do desempenho no ano avaliado.
8. **Limites e leituras incorretas:** Doze pontos por horizonte não provam um padrão anual generalizável; compara a regra global. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-d_pax_examples — d_pax_examples

1. **Localização:** `research/ml-showcase/figures/d_pax_examples.png` (+ `.svg`).
2. **Modelo/experimento:** D-pax.
3. **Objetivo:** Mesmos extremos da web em painéis estáticos.
4. **Eixos, unidade e legenda:** X: dia/mês de 2023, h=1; Y: paid passengers. Três séries identificadas na legenda.
5. **Dados e proveniência:** `analysis.py::fig_examples_a/fig_examples_routes`, seleção retrospectiva pelos erros agrupados.
6. **Leitura estatística:** Título histórico associa WAPE agrupado a uma curva h=1: a distinção é obrigatória nesta leitura.
7. **Conclusão sustentada:** Permite inspecionar visualmente entidades escolhidas após a avaliação.
8. **Limites e leituras incorretas:** Casos extremos não são representativos. Figuras históricas mantidas; errata documenta o escopo do score.

## web-d_seats-monthly — Actual vs predicted, by target month

1. **Localização:** `web/components/dashboard/ml-showcase.tsx` TaskView / LinesChart.
2. **Modelo/experimento:** D-seats.
3. **Objetivo:** Comparar nível observado, previsão de seleção e referência.
4. **Eixos, unidade e legenda:** X: janeiro a dezembro de 2023. Y: seats. Atual, LightGBM e melhor baseline global.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; monthly, filtrado por horizon; B usa assentos observados como pesos de todas as séries.
6. **Leitura estatística:** A proximidade de totais/médias avalia nível agregado, não igualdade por unidade. Lower is better; cor do modelo=chart-1/azul, baseline=muted/cinza; atual=ink; tokens DAY/NIGHT.
7. **Conclusão sustentada:** Revela desvios temporais e de nível do experimento selecionado.
8. **Limites e leituras incorretas:** Cancelamentos de erro podem ocultar falhas de rota/dia. Só este gráfico acompanha o seletor de horizonte; comparação fixa no melhor baseline agregado.

## web-d_seats-volume — Error by traffic volume

1. **Localização:** `web/components/dashboard/ml-showcase.tsx` TaskView / LinesChart.
2. **Modelo/experimento:** D-seats.
3. **Objetivo:** Inspecionar heterogeneidade do erro por tamanho histórico.
4. **Eixos, unidade e legenda:** X: decis 1–10 da feature SIZE conhecida no cutoff. Y: WAPE, %, modelo e baseline.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; by_volume_decile; níveis A=hist_level_56, B=hist_seats_mean_12, D=hist_pax/seats_mean_12.
6. **Leitura estatística:** Agrupa observações por feature histórica; limites dos decis são estimados em 2023. Lower is better; cor do modelo=chart-1/azul, baseline=muted/cinza; atual=ink; tokens DAY/NIGHT.
7. **Conclusão sustentada:** Sustenta diferenças descritivas de dificuldade entre estratos observados.
8. **Limites e leituras incorretas:** Não é WAPE por número de unidades nem ranking futuro. Decis não são limiares fixados no treino; os horizontes estão agrupados.

## web-d_seats-entity — Largest units, by directed route

1. **Localização:** `web/components/dashboard/ml-showcase.tsx` TaskView / PairBars.
2. **Modelo/experimento:** D-seats.
3. **Objetivo:** Comparar modelo e regra nas maiores entidades observadas.
4. **Eixos, unidade e legenda:** Entidade no eixo categórico; comprimento horizontal= WAPE, %. Azul modelo, cinza baseline.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; by_entity[:10], agrupado por aeroporto A, companhia B ou rota D; tamanho por volume observado em 2023.
6. **Leitura estatística:** Ranking é retrospectivo e os erros são recalculados sobre as linhas de cada entidade. Lower is better; cor do modelo=chart-1/azul, baseline=muted/cinza; atual=ink; tokens DAY/NIGHT.
7. **Conclusão sustentada:** Mostra onde o modelo erra mais/menos entre grandes entidades efetivamente avaliadas.
8. **Limites e leituras incorretas:** B agrega rotas de cada companhia; não é erro por companhia×rota individual. Não representa entidades pequenas nem fatia de mercado; horizontes repetem targets.

## web-d_seats-residuals — Residuals

1. **Localização:** `web/components/dashboard/ml-showcase.tsx` TaskView / Histogram.
2. **Modelo/experimento:** D-seats.
3. **Objetivo:** Inspecionar assimetria, dispersão e caudas dos erros assinados.
4. **Eixos, unidade e legenda:** X: (predito−real)×100 em pp para B, ou (predito−real)/real para volumes. Y: número não ponderado de linhas; duas cores sobrepostas.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; residuals; 31,473 linhas incluídas de 33,762; bins fixos ±30 pp B ou ±100% volumes.
6. **Leitura estatística:** Positivo é sobreprevisão. Caudas são acumuladas no primeiro/último bin; p10/p50/p90 usam resíduos sem clipping. Lower is better; cor do modelo=chart-1/azul, baseline=muted/cinza; atual=ink; tokens DAY/NIGHT.
7. **Conclusão sustentada:** Sustenta descrição empírica de sinais e caudas na amostra incluída.
8. **Limites e leituras incorretas:** Volumes zero ficam fora do erro relativo; distribuição não ponderada pode discordar de WAPE/MAE ponderado. p10–p90 não é intervalo preditivo futuro.

## web-d_seats-scatter — Actual vs predicted, row level

1. **Localização:** `web/components/dashboard/ml-showcase.tsx` TaskView / Scatter.
2. **Modelo/experimento:** D-seats.
3. **Objetivo:** Ver alinhamento entre observações e predições pontuais.
4. **Eixos, unidade e legenda:** X: observado, Y: LightGBM, na unidade seats; diagonal y=x. Log nos dois eixos de volumes; linear para B.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; scatter: até 400 pares de validação h=1, amostra com seed 11; contém informação de linhas, embora limitada.
6. **Leitura estatística:** Abaixo da diagonal é subprevisão. Amostra é diagnóstica; score usa todas as linhas comparáveis. Lower is better; cor do modelo=chart-1/azul, baseline=muted/cinza; atual=ink; tokens DAY/NIGHT.
7. **Conclusão sustentada:** Sustenta o padrão visual de dispersão da amostra, sem estimar acurácia por densidade aparente.
8. **Limites e leituras incorretas:** Pares não positivos são removidos nos eixos log; pontos sobrepostos escondem densidade. Sem baseline ou intervalo de previsão por ponto.

## web-d_seats-gain — What the trees split on

1. **Localização:** `web/components/dashboard/ml-showcase.tsx` TaskView / BarList.
2. **Modelo/experimento:** D-seats.
3. **Objetivo:** Descrever como o booster de seleção distribuiu ganho de splits.
4. **Eixos, unidade e legenda:** Y: nome da feature; X/comprimento: fração do ganho total, exibida em %; top 10.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; top_features_by_gain dos reports/models; não recalculado do booster final refitado.
6. **Leitura estatística:** É importância interna do fitting, enviesável por cardinalidade e correlação. Lower is better; cor do modelo=chart-1/azul, baseline=muted/cinza; atual=ink; tokens DAY/NIGHT.
7. **Conclusão sustentada:** Permite verificar se o modelo usa níveis, calendário e identidades plausíveis.
8. **Limites e leituras incorretas:** Não é SHAP, efeito causal, contribuição de uma predição nem permutation importance em validação. Top 10 não soma necessariamente 100%.

## web-d_seats-horizon-table — Error by horizon

1. **Localização:** `ml-showcase.tsx` / DataTable.
2. **Modelo/experimento:** D-seats.
3. **Objetivo:** Comparar todas as regras e o viés em cada horizonte.
4. **Eixos, unidade e legenda:** Linhas: horizonte origem→target; colunas: WAPE, % de cada método e viés assinado.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`; by_horizon. Viés B corrigido usa seat_weighted_bias_model; demais usam bias_model.
6. **Leitura estatística:** Selecionar o menor ponto não demonstra significância. Os CIs por horizonte estão em EXPERIMENT_RESULTS.
7. **Conclusão sustentada:** A e B h=1/h=3 não têm ganho conclusivo; D h=6 não demonstra superioridade.
8. **Limites e leituras incorretas:** A regra global pode mudar por horizonte. Tabela não segue o seletor do gráfico mensal.

## web-d_seats-kpi-model — model KPI

1. **Localização:** `ml-showcase.tsx` / StatTile.
2. **Modelo/experimento:** D-seats.
3. **Objetivo:** Erro do LightGBM no conjunto comparável.
4. **Eixos, unidade e legenda:** Sem eixos; número e unidade explícitos. CIs de erro quando exibidos.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`
6. **Leitura estatística:** Valores agregam horizontes e linhas comparáveis; não são métricas de teste.
7. **Conclusão sustentada:** A mantém baseline; B/D têm evidência histórica agregada, sujeita às ressalvas auditadas.
8. **Limites e leituras incorretas:** Um percentual de erro não é accuracy; a decisão histórica não valida o modelo corrigido futuro.

## web-d_seats-kpi-baseline — baseline KPI

1. **Localização:** `ml-showcase.tsx` / StatTile.
2. **Modelo/experimento:** D-seats.
3. **Objetivo:** Menor erro entre baselines no mesmo conjunto.
4. **Eixos, unidade e legenda:** Sem eixos; número e unidade explícitos. CIs de erro quando exibidos.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`
6. **Leitura estatística:** Valores agregam horizontes e linhas comparáveis; não são métricas de teste.
7. **Conclusão sustentada:** A mantém baseline; B/D têm evidência histórica agregada, sujeita às ressalvas auditadas.
8. **Limites e leituras incorretas:** Um percentual de erro não é accuracy; a decisão histórica não valida o modelo corrigido futuro.

## web-d_seats-kpi-difference — difference KPI

1. **Localização:** `ml-showcase.tsx` / StatTile.
2. **Modelo/experimento:** D-seats.
3. **Objetivo:** Erro modelo menos melhor baseline; diferença pareada.
4. **Eixos, unidade e legenda:** Sem eixos; número e unidade explícitos. CIs de erro quando exibidos.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`
6. **Leitura estatística:** Valores agregam horizontes e linhas comparáveis; não são métricas de teste.
7. **Conclusão sustentada:** A mantém baseline; B/D têm evidência histórica agregada, sujeita às ressalvas auditadas.
8. **Limites e leituras incorretas:** Um percentual de erro não é accuracy; a decisão histórica não valida o modelo corrigido futuro.

## web-d_seats-kpi-bias — bias KPI

1. **Localização:** `ml-showcase.tsx` / StatTile.
2. **Modelo/experimento:** D-seats.
3. **Objetivo:** Erro assinado; B ponderado por assentos em pp, volumes relativos em %.
4. **Eixos, unidade e legenda:** Sem eixos; número e unidade explícitos. CIs de erro quando exibidos.
5. **Dados e proveniência:** `web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`
6. **Leitura estatística:** Valores agregam horizontes e linhas comparáveis; não são métricas de teste.
7. **Conclusão sustentada:** A mantém baseline; B/D têm evidência histórica agregada, sujeita às ressalvas auditadas.
8. **Limites e leituras incorretas:** Um percentual de erro não é accuracy; a decisão histórica não valida o modelo corrigido futuro.

## paper-d_seats_actual_vs_predicted_monthly — d_seats_actual_vs_predicted_monthly

1. **Localização:** `research/ml-showcase/figures/d_seats_actual_vs_predicted_monthly.png` (+ `.svg`).
2. **Modelo/experimento:** D-seats.
3. **Objetivo:** Comparar nível observado, previsão de seleção e referência.
4. **Eixos, unidade e legenda:** X: janeiro a dezembro de 2023. Y: seats. Atual, LightGBM e melhor baseline global.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; monthly, filtrado por horizon; B usa assentos observados como pesos de todas as séries.
6. **Leitura estatística:** A proximidade de totais/médias avalia nível agregado, não igualdade por unidade.
7. **Conclusão sustentada:** Revela desvios temporais e de nível do experimento selecionado.
8. **Limites e leituras incorretas:** Cancelamentos de erro podem ocultar falhas de rota/dia. Só este gráfico acompanha o seletor de horizonte; comparação fixa no melhor baseline agregado. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-d_seats_scatter — d_seats_scatter

1. **Localização:** `research/ml-showcase/figures/d_seats_scatter.png` (+ `.svg`).
2. **Modelo/experimento:** D-seats.
3. **Objetivo:** Ver alinhamento entre observações e predições pontuais.
4. **Eixos, unidade e legenda:** X: observado, Y: LightGBM, na unidade seats; diagonal y=x. Log nos dois eixos de volumes; linear para B.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; scatter_sample com n≤4.000 e seed 7; distingue-se dos 400 pares seed 11 da web.
6. **Leitura estatística:** Abaixo da diagonal é subprevisão. Amostra é diagnóstica; score usa todas as linhas comparáveis.
7. **Conclusão sustentada:** Sustenta o padrão visual de dispersão da amostra, sem estimar acurácia por densidade aparente.
8. **Limites e leituras incorretas:** Pares não positivos são removidos nos eixos log; pontos sobrepostos escondem densidade. Sem baseline ou intervalo de previsão por ponto. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-d_seats_residuals — d_seats_residuals

1. **Localização:** `research/ml-showcase/figures/d_seats_residuals.png` (+ `.svg`).
2. **Modelo/experimento:** D-seats.
3. **Objetivo:** Inspecionar assimetria, dispersão e caudas dos erros assinados.
4. **Eixos, unidade e legenda:** X: (predito−real)×100 em pp para B, ou (predito−real)/real para volumes. Y: número não ponderado de linhas; duas cores sobrepostas.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; residuals; 31,473 linhas incluídas de 33,762; bins fixos ±30 pp B ou ±100% volumes.
6. **Leitura estatística:** Positivo é sobreprevisão. Caudas são acumuladas no primeiro/último bin; p10/p50/p90 usam resíduos sem clipping.
7. **Conclusão sustentada:** Sustenta descrição empírica de sinais e caudas na amostra incluída.
8. **Limites e leituras incorretas:** Volumes zero ficam fora do erro relativo; distribuição não ponderada pode discordar de WAPE/MAE ponderado. p10–p90 não é intervalo preditivo futuro. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-d_seats_by_horizon — d_seats_by_horizon

1. **Localização:** `research/ml-showcase/figures/d_seats_by_horizon.png` (+ `.svg`).
2. **Modelo/experimento:** D-seats.
3. **Objetivo:** Comparar erros por horizonte em barras agrupadas.
4. **Eixos, unidade e legenda:** X: h=1/3 ou 1/3/6; Y: WAPE, %; uma barra por método.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; by_horizon, todas as regras.
6. **Leitura estatística:** Mesmo conjunto de linhas por método; só estimativas pontuais no gráfico.
7. **Conclusão sustentada:** Revela heterogeneidade por horizonte, sem dispensar os intervalos pareados.
8. **Limites e leituras incorretas:** Não declarar superioridade apenas pelo menor comprimento; não há CI de diferença desenhado. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-d_seats_by_volume — d_seats_by_volume

1. **Localização:** `research/ml-showcase/figures/d_seats_by_volume.png` (+ `.svg`).
2. **Modelo/experimento:** D-seats.
3. **Objetivo:** Inspecionar heterogeneidade do erro por tamanho histórico.
4. **Eixos, unidade e legenda:** X: decis 1–10 da feature SIZE conhecida no cutoff. Y: WAPE, %, modelo e baseline.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; by_volume_decile; níveis A=hist_level_56, B=hist_seats_mean_12, D=hist_pax/seats_mean_12.
6. **Leitura estatística:** Agrupa observações por feature histórica; limites dos decis são estimados em 2023.
7. **Conclusão sustentada:** Sustenta diferenças descritivas de dificuldade entre estratos observados.
8. **Limites e leituras incorretas:** Não é WAPE por número de unidades nem ranking futuro. Decis não são limiares fixados no treino; os horizontes estão agrupados. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-d_seats_by_entity — d_seats_by_entity

1. **Localização:** `research/ml-showcase/figures/d_seats_by_entity.png` (+ `.svg`).
2. **Modelo/experimento:** D-seats.
3. **Objetivo:** Comparar modelo e regra nas maiores entidades observadas.
4. **Eixos, unidade e legenda:** Entidade no eixo categórico; comprimento horizontal= WAPE, %. Azul modelo, cinza baseline.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; by_entity: até 20 entidades, em vez das 10 da web.
6. **Leitura estatística:** Ranking é retrospectivo e os erros são recalculados sobre as linhas de cada entidade.
7. **Conclusão sustentada:** Mostra onde o modelo erra mais/menos entre grandes entidades efetivamente avaliadas.
8. **Limites e leituras incorretas:** B agrega rotas de cada companhia; não é erro por companhia×rota individual. Não representa entidades pequenas nem fatia de mercado; horizontes repetem targets. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-d_seats_feature_gain — d_seats_feature_gain

1. **Localização:** `research/ml-showcase/figures/d_seats_feature_gain.png` (+ `.svg`).
2. **Modelo/experimento:** D-seats.
3. **Objetivo:** Descrever como o booster de seleção distribuiu ganho de splits.
4. **Eixos, unidade e legenda:** Y: nome da feature; X/comprimento: fração do ganho total, exibida em %; top 10.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; top_features_by_gain dos reports/models; não recalculado do booster final refitado.
6. **Leitura estatística:** É importância interna do fitting, enviesável por cardinalidade e correlação.
7. **Conclusão sustentada:** Permite verificar se o modelo usa níveis, calendário e identidades plausíveis.
8. **Limites e leituras incorretas:** Não é SHAP, efeito causal, contribuição de uma predição nem permutation importance em validação. Top 10 não soma necessariamente 100%. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-d_seats_error_by_month — d_seats_error_by_month

1. **Localização:** `research/ml-showcase/figures/d_seats_error_by_month.png` (+ `.svg`).
2. **Modelo/experimento:** D-seats.
3. **Objetivo:** Examinar a variação do erro de unidade por target-month.
4. **Eixos, unidade e legenda:** X: mês de 2023; Y: WAPE, %. Painéis por horizonte, curvas modelo e baseline.
5. **Dados e proveniência:** `analysis.py` e validation_frame → predições 2023; monthly.model_error/baseline_error.
6. **Leitura estatística:** Erro calculado antes de agregar; não é erro entre os totais do gráfico de nível.
7. **Conclusão sustentada:** Mostra sazonalidade do desempenho no ano avaliado.
8. **Limites e leituras incorretas:** Doze pontos por horizonte não provam um padrão anual generalizável; compara a regra global. O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.

## paper-overview_model_vs_baseline — overview_model_vs_baseline

1. **Localização:** `figures/overview_model_vs_baseline.{png,svg}`.
2. **Modelo/experimento:** A/B/D-pax/D-seats.
3. **Objetivo:** Comparar cada target com seu próprio baseline.
4. **Eixos, unidade e legenda:** Painéis por target; erro principal na unidade própria e anotações de decisão/intervalo.
5. **Dados e proveniência:** `analysis.py::fig_overview` e reports/models.
6. **Leitura estatística:** Comparação válida dentro de cada tarefa; MAE de ocupação e WAPE não compartilham semântica.
7. **Conclusão sustentada:** A não supera conclusivamente a referência; B/D têm ganho agregado histórico.
8. **Limites e leituras incorretas:** Não ranquear A contra B pela magnitude; adoção está condicionada a uma única validação e à falha D descoberta.

## paper-eda_monthly_market — eda_monthly_market

1. **Localização:** `figures/eda_monthly_market.{png,svg}`.
2. **Modelo/experimento:** Contexto dos dados.
3. **Objetivo:** Mostrar histórico da oferta/demanda atendida e janelas do estudo.
4. **Eixos, unidade e legenda:** X: meses 2000–2025; Y: passageiros pagos/assentos mensais; duas linhas, faixas validação/teste e lacunas.
5. **Dados e proveniência:** `analysis.py::eda`, analytics/fact_route_month e calendário; figura já existente, não regenerada nesta auditoria.
6. **Leitura estatística:** É descrição observada do mercado, não série de previsão.
7. **Conclusão sustentada:** Sustenta descrição histórica e a ausência global de quatro meses.
8. **Limites e leituras incorretas:** Inclui totais do período de teste já expostos; não prova teste cego. Não foi relida a série 2024–2025 para esta auditoria.

## paper-eda_concentration — eda_concentration

1. **Localização:** `figures/eda_concentration.{png,svg}`.
2. **Modelo/experimento:** Contexto dos dados.
3. **Objetivo:** Explicar a concentração do universo antes da validação.
4. **Eixos, unidade e legenda:** X: Top N, escala log; Y: participação acumulada em 2022. Aeroportos por movimentos e rotas por passageiros.
5. **Dados e proveniência:** `analysis.py::eda`, fact_airport_month e fact_route_month, somente ranking 2022 na figura.
6. **Leitura estatística:** Curvas têm unidades/universos diferentes apesar de compartilharem participação percentual.
7. **Conclusão sustentada:** Justifica examinar grandes unidades; não demonstra cobertura universal ou escolha ótima do top 50.
8. **Limites e leituras incorretas:** A escolhe top 50 por cutoff, não usa esta curva de 2022 como lista fixa para todos os anos.

## registry-a-baseline — Model registry: A / baseline

1. **Localização:** `web/components/dashboard/data-views.tsx::ModelPanel/MetricList`.
2. **Modelo/experimento:** A.
3. **Objetivo:** Identificar o método e a seleção histórica, sem confundir disponibilidade com serving preditivo.
4. **Eixos, unidade e legenda:** Sem eixos; lista de métricas principais, unidade e período; badge Selected method quando selecionado.
5. **Dados e proveniência:** GET /v2/models, exportado de reports/models por _validation_cards; D contém pax e seats.
6. **Leitura estatística:** Valores são de validação 2023; seleção usa critério agregado (ambos os targets para D).
7. **Conclusão sustentada:** Permite rastrear baseline e LightGBM lado a lado, com A mantendo a regra.
8. **Limites e leituras incorretas:** Pode faltar se o payload não foi exportado/API falhar; o showcase estático é independente. Não é nova curva ou prova de forecast operacional.

## registry-a-lightgbm — Model registry: A / lightgbm

1. **Localização:** `web/components/dashboard/data-views.tsx::ModelPanel/MetricList`.
2. **Modelo/experimento:** A.
3. **Objetivo:** Identificar o método e a seleção histórica, sem confundir disponibilidade com serving preditivo.
4. **Eixos, unidade e legenda:** Sem eixos; lista de métricas principais, unidade e período; badge Selected method quando selecionado.
5. **Dados e proveniência:** GET /v2/models, exportado de reports/models por _validation_cards; D contém pax e seats.
6. **Leitura estatística:** Valores são de validação 2023; seleção usa critério agregado (ambos os targets para D).
7. **Conclusão sustentada:** Permite rastrear baseline e LightGBM lado a lado, com A mantendo a regra.
8. **Limites e leituras incorretas:** Pode faltar se o payload não foi exportado/API falhar; o showcase estático é independente. Não é nova curva ou prova de forecast operacional.

## registry-b-baseline — Model registry: B / baseline

1. **Localização:** `web/components/dashboard/data-views.tsx::ModelPanel/MetricList`.
2. **Modelo/experimento:** B.
3. **Objetivo:** Identificar o método e a seleção histórica, sem confundir disponibilidade com serving preditivo.
4. **Eixos, unidade e legenda:** Sem eixos; lista de métricas principais, unidade e período; badge Selected method quando selecionado.
5. **Dados e proveniência:** GET /v2/models, exportado de reports/models por _validation_cards; D contém pax e seats.
6. **Leitura estatística:** Valores são de validação 2023; seleção usa critério agregado (ambos os targets para D).
7. **Conclusão sustentada:** Permite rastrear baseline e LightGBM lado a lado, com A mantendo a regra.
8. **Limites e leituras incorretas:** Pode faltar se o payload não foi exportado/API falhar; o showcase estático é independente. Não é nova curva ou prova de forecast operacional.

## registry-b-lightgbm — Model registry: B / lightgbm

1. **Localização:** `web/components/dashboard/data-views.tsx::ModelPanel/MetricList`.
2. **Modelo/experimento:** B.
3. **Objetivo:** Identificar o método e a seleção histórica, sem confundir disponibilidade com serving preditivo.
4. **Eixos, unidade e legenda:** Sem eixos; lista de métricas principais, unidade e período; badge Selected method quando selecionado.
5. **Dados e proveniência:** GET /v2/models, exportado de reports/models por _validation_cards; D contém pax e seats.
6. **Leitura estatística:** Valores são de validação 2023; seleção usa critério agregado (ambos os targets para D).
7. **Conclusão sustentada:** Permite rastrear baseline e LightGBM lado a lado, com A mantendo a regra.
8. **Limites e leituras incorretas:** Pode faltar se o payload não foi exportado/API falhar; o showcase estático é independente. Não é nova curva ou prova de forecast operacional.

## registry-d-baseline — Model registry: D / baseline

1. **Localização:** `web/components/dashboard/data-views.tsx::ModelPanel/MetricList`.
2. **Modelo/experimento:** D.
3. **Objetivo:** Identificar o método e a seleção histórica, sem confundir disponibilidade com serving preditivo.
4. **Eixos, unidade e legenda:** Sem eixos; lista de métricas principais, unidade e período; badge Selected method quando selecionado.
5. **Dados e proveniência:** GET /v2/models, exportado de reports/models por _validation_cards; D contém pax e seats.
6. **Leitura estatística:** Valores são de validação 2023; seleção usa critério agregado (ambos os targets para D).
7. **Conclusão sustentada:** Permite rastrear baseline e LightGBM lado a lado, com A mantendo a regra.
8. **Limites e leituras incorretas:** Pode faltar se o payload não foi exportado/API falhar; o showcase estático é independente. Não é nova curva ou prova de forecast operacional.

## registry-d-lightgbm — Model registry: D / lightgbm

1. **Localização:** `web/components/dashboard/data-views.tsx::ModelPanel/MetricList`.
2. **Modelo/experimento:** D.
3. **Objetivo:** Identificar o método e a seleção histórica, sem confundir disponibilidade com serving preditivo.
4. **Eixos, unidade e legenda:** Sem eixos; lista de métricas principais, unidade e período; badge Selected method quando selecionado.
5. **Dados e proveniência:** GET /v2/models, exportado de reports/models por _validation_cards; D contém pax e seats.
6. **Leitura estatística:** Valores são de validação 2023; seleção usa critério agregado (ambos os targets para D).
7. **Conclusão sustentada:** Permite rastrear baseline e LightGBM lado a lado, com A mantendo a regra.
8. **Limites e leituras incorretas:** Pode faltar se o payload não foi exportado/API falhar; o showcase estático é independente. Não é nova curva ou prova de forecast operacional.

## registry-c — Model registry: C not trained

1. **Localização:** `web/components/dashboard/data-views.tsx::MlStudioView`.
2. **Modelo/experimento:** C.
3. **Objetivo:** Expor ausência de treinamento sem fabricar score.
4. **Eixos, unidade e legenda:** Sem eixos ou métricas; status textual.
5. **Dados e proveniência:** GET /v2/models, card module-c criado em serving/export.py.
6. **Leitura estatística:** O gate de qualidade de bagagem não é treinamento de modelo.
7. **Conclusão sustentada:** Não há previsão C validada.
8. **Limites e leituras incorretas:** Não interpretar o status como inferência de bagagem individual ou recomendação de cobrança.
