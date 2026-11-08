# Defesa técnica — iFood GenAI Internship / AI Builder

Este guia usa evidência do repositório; não supõe critérios privados do processo seletivo.
Separe o que você implementou do que está planejado e do que uma auditoria posterior corrigiu.
Não apresente redes legadas, bagagem C ou forecasts futuros como funcionalidades validadas.

## Apresentação de 90 segundos

“Construí uma plataforma de inteligência de aviação com ingestão auditável, camada analítica,
API e interface. Na parte supervisionada comparei quatro regressores LightGBM com regras
simples, usando cortes por disponibilidade e validação histórica de 2023. O principal resultado
não é que IA sempre vence: em movimentos aeroportuários eu manteria o baseline. Em ocupação
e volumes existem ganhos agregados históricos, mas também viés, diferenças por horizonte e
um erro de tratamento de meses ausentes descoberto na auditoria. Corrigi o caminho futuro sem
reescrever os modelos ou os scores congelados. A interface distingue essas evidências de uma
previsão atual. O teste de 2024–2025 não foi pontuado e não é completamente cego. O Analyst é
uma camada separada de linguagem sobre ferramentas de leitura; não transforma isso em previsão.”

## Demonstração sugerida

1. Abrir `/dashboard/ml-studio` local. Mostrar A: 10,10% contra 10,30%, mas CI da diferença inclui
   zero. Explicar por que um ganho pontual não paga a complexidade de um booster.
2. Abrir “How to read this evaluation”: fitting/stopping/validação, disponibilidade e clusters.
3. Mostrar B: 6,06 pp contra 6,54 pp; definir pp com exemplo 80%→86% = 6 pp, não 6% relativo.
   Mostrar viés ponderado −0,05 pp e explicar por que o KPI anterior relativo podia inverter o sinal.
4. Mostrar D-pax: 22,24% contra 25,31%; abrir a tabela: 6 meses não supera a referência.
   Mostrar viés −12,21%, aviso dos targets ausentes e distribuição incluindo a ressalva dos zeros.
5. Mudar o horizonte: só a curva mensal responde; scatter/casos usam h=1, outras distribuições
   agrupam horizontes. Mostrar tooltip, legenda e a diferença entre total e erro por unidade.
6. Abrir `audit.json`: reprodução de métricas, hashes, origens e ausência de refit/holdout.
   Se o backend estiver fora do ar, o showcase estático ainda é inspecionável; não mascarar erro da API.

## Perguntas difíceis e respostas sustentáveis

### Isso é GenAI? Por que usar este projeto numa vaga de AI Builder?

Os quatro modelos são forecasting supervisionado tabular, não modelos generativos. A parte
GenAI é o Analyst que consulta ferramentas determinísticas e descreve resultados. O valor
transferível é construir o ciclo dado→experimento→contrato→interface→avaliação, saber recusar
claims sem evidência e separar comportamento probabilístico de verificação numérica. Não
alegar que LightGBM é um LLM ou que esta auditoria avaliou a v3 do Claude.
Evidência: `src/anac/models`, `src/anac/agent`, `src/anac/api/app.py` no commit base.

### Por que não uma rede neural ou um agente para prever passageiros?

Dados tabulares com histórico agregado, categorias e calendário permitem uma referência
computacional simples. LightGBM trata não linearidades e missing com custo pequeno. Não há
experimento controlado comparando-o a todas as redes; os scripts LSTM/Transformer legados
não são evidência de desempenho atual. Um agente textual não substitui uma avaliação temporal
nem resolve ausência de target/tarifas. Começaria pelo baseline e custo incremental medido.
Evidência: `configs/models.toml`, SPECS e baselines.

### Onde exatamente você evitou leakage?

A construção de features recebe histórico já cortado e recusa fonte depois do cutoff.
Calendário futuro é permitido; resultados de operação não são. Stamps e schemas são fechados,
identidades/vocabulários vêm do fitting e há purge por distância nas fronteiras. Testes
alteram dados após o corte e exigem mesmas features. Ainda assim, dados revisados sem vintages
podem produzir otimismo: o controle temporal não prova disponibilidade histórica perfeita.
Evidência: `daily.py`, `monthly.py`, `contracts.py`, `splits.py`, testes de leakage.

### Assentos futuros foram usados no modelo B?

Assentos observados no target são peso de treino e avaliação, não feature de entrada.
As features de assentos são médias/lags conhecidos no cutoff. Essa avaliação dá mais peso a
operações grandes e é condicional à operação; não pode ser usada para alegar previsão de
cancelamento. O viés agora segue os mesmos pesos; o histograma continua não ponderado.

### Por que normalizar volumes pelo nível recente?

Árvores não extrapolam tendência numérica como uma regressão linear por padrão. Predizer
uma razão ao nível e reescalar permite acompanhar nível conhecido recente. Peso=nível
mantém L1 alinhada ao erro absoluto em volume. Isso não elimina mudanças de regime nem
subprevisão; o crescimento de 2023 e a falha D são limitações documentadas, não causalidade provada.

### WAPE de 10% significa 90% de acurácia?

Não. É erro absoluto total dividido pelo volume total. Não é classificação, pode superar
100%, e grandes unidades dominam. Zeros observados contam no numerador, mas não no denominador;
por isso o histograma relativo exclui zeros e não tem a mesma população da métrica principal.

### Seu teste é realmente cego?

Não completamente. O scoring de 2024–2025 não foi executado, mas totais anuais e algumas séries
foram vistos numa auditoria anterior (decisão 3). Não alego resultado de teste. A evidência
atual é validação 2023; seria necessário registrar o protocolo e considerar novo período
prospectivo antes de chamar o resultado de confirmação independente.

### Como você pode provar um ganho com só 12 meses?

A regra registrada usa CI pareado resamplando clusters de target-month. Preserva correlação
dentro do mês, mas não a serial entre meses; são poucos clusters. A escolha do baseline e
vários horizontes não têm correção de multiplicidade. Eu digo “evidência nesse ano sob esse
estimador”, não “ganho universal comprovado”. Mais origens/anos e testes de sensibilidade são pendências.

### Por que você não escolheu o LightGBM A?

O ganho pontual de cerca de 0,21 pp de WAPE tem CI aproximadamente [−0,84;+0,35].
A referência recente é competitiva, mais simples e foi mantida na decisão histórica.
No B o ganho agregado não autoriza afirmar ganho em h=1 ou h=3; os CIs individuais incluem zero.

### O que a auditoria descobriu que muda sua confiança no projeto?

O loader D transformava meses globalmente ausentes em zeros de rotas. Foram 11.689/11.692
linhas de fitting dos targets pax/seats. Corrigi e testei o caminho futuro; preservei v1 e os
scores históricos. Sem novo treinamento não sei o desempenho corrigido nem quanto do viés
veio dessa falha. Não apresentaria D como pronto para adoção antes de uma nova versão.

### Por que o hash do modelo não basta para reproduzir tudo?

O manifest autenticava os boosters, mas não vocabulários; o digest do dataset usa nomes e
tamanhos; o treino registra uma árvore Git suja. Hash agora comprova identidade dos inputs
lidos nesta auditoria, não reconstitui sozinho todo o código e os dados históricos originais.
A reprodução de métricas das predições salvas é forte para os scores, mas diferente de
refazer o treinamento a partir de um commit limpo. Após a correção D, um refit idêntico é
esperadamente impossível sem executar deliberadamente o código legado defeituoso.

### Você usou o booster final para validar 2023?

Não. Ele foi refitado incluindo parte de 2023. Usei as predições de seleção persistidas,
com join 1:1, igualdade dos targets, comparação com relatórios e um oráculo NumPy.
Confundir os dois modelos produziria uma validação resubstituída e otimista.

### A importância de uma feature diz o que causa mais passageiros?

Não. Ganho de split é diagnóstico interno; features correlacionadas e categorias com muitas
modalidades podem dominar. Não é SHAP, efeito de intervenção ou elasticidade. Seria preciso
outro desenho causal para recomendar decisões comerciais.

### Os melhores exemplos foram escolhidos depois dos resultados?

Sim, declaradamente. Entre as maiores entidades, escolhem-se os extremos pelo erro agrupado;
a curva mostrada usa h=1 e o score exibido é agrupado. Eles explicam falhas, não representam
a distribuição inteira. O headline é calculado no universo comparável completo, não nesses casos.

### Qual a diferença entre AP e Brier na pressão?

AP mede ranking de eventos positivos em limiares; Brier mede erro quadrático de probabilidades.
O LightGBM tem AP um pouco maior, mas pior Brier relatado. Corrigi o tratamento de empates
em AP; Brier não foi reproduzido independentemente porque faltam taxas/predições de calibração
persistidas. Não venderia o score bruto como probabilidade calibrada nem como preço.

### Como o módulo C se relaciona a cobrança de bagagem?

C não foi treinado. O gate é de qualidade de um target agregado de bagagem despachada,
não comportamento individual ou eficácia de cobrança. O excesso foi rejeitado por refletir
registro; a mudança de método do gate após resultados é uma limitação explícita.
Não existe target de tarifa na fonte e o proxy legado não o substitui.

### O que você melhoraria primeiro com prazo limitado?

Primeiro congelaria o protocolo e corrigiria/proveria os meses ausentes, com uma versão nova
que registre conteúdo, código e vocabulários. Depois testaria sensibilidade de defasagem,
período de treino e regime, mantendo o holdout fora de tuning. Só então serviria o método
escolhido com monitoramento. Mais gráficos ou mais árvores não substituem essas etapas.

## Afirmações que não devem aparecer na apresentação

- “Modelos neurais publicados”, “C treinado”, “teste passou” ou “previsões futuras em produção”.
- “Ocupação B é RPK/ASK”, “WAPE é accuracy” ou “passageiros são pessoas únicas”.
- “AP prova calibração”, “95% de chance de a próxima demanda estar nessa faixa” ou “SHAP causal”.
- “Zero significa mês sem arquivo”, “v1 corrigido já ganhou mais” ou “2024–2025 é completamente cego”.
- “O Analyst generativo é o modelo de previsão” ou “o projeto determina preço/lucro sem tarifas”.

O relatório/PDF anterior é evidência histórica: acompanhar com EXPERIMENT_RESULTS e os avisos
revisados. A decisão de abrir holdout, promover novos modelos ou publicar alterações é do dono.
