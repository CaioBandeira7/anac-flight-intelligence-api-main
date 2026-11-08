# Guia das previsões: o que existe e o que falta

## Quatro situações diferentes

| Situação | Estado verificado | Interpretação correta |
|---|---|---|
| Predições históricas de validação | Implementadas e salvas para 2023 | Seleção LightGBM treinada/stopped antes de 2023, features cortadas por origem, comparações com regras |
| Backtesting temporal | Um ano reservado, múltiplas origens e horizontes | Não é avaliação em vários anos independentes nem rolling-refit dos boosters a cada origem |
| Inferência em novos dados | Helper `models/train.py::predict` existe | Função de baixo nível requer features/vocabulário/escala compatíveis; não há serviço operacional de novas origens |
| Previsões futuras servidas | Não implementadas | O ML Studio não solicita target futuro, não serve demanda atual, preços ou recomendações |
| Predições no teste histórico 2024–2025 | Não pontuadas | Holdout fechado para scoring; parcialmente exposto em agregados por decisão anterior; não completamente cego |

Trocar a aba de experimento/horizonte não executa booster, treinamento ou chamada ao LLM.
O JSON carrega resultados históricos. Os exemplos e os 400 pares amostrados são dados de
validação já persistidos; não geram previsões novas nem substituem o score sobre todas as linhas.

## Contrato temporal

Se a origem é O e o horizonte h, o target é `O+h`; cutoff é `O−2` (mês de referência).
Exemplo conceitual do protocolo: origem 2022-12, h=1, target 2023-01, último mês conhecido
2022-10. No A diário, cutoff é o último dia desse mês; para h=3 o target é 2023-03.
Calendário do target é conhecido antecipadamente, porém sua operação/passageiros/assentos
não entram nas features. Assentos observados só pesam a função de treino/avaliação B.
Em produção eles não estariam disponíveis para ponderar resultados ainda não observados.

O split é por target, com purge por distância; o treino precisa estar disponível quando se
faz a primeira previsão da validação. Early stopping tem purge independente em 2022.
As datas absolutas são excluídas do booster, não as features de calendário.

## Exemplos reais dos arquivos publicados

A tabela mostra pontos realmente armazenados em `showcase.json`. São casos extremos escolhidos
retrospectivamente (não amostras aleatórias nem evidência prospectiva).

| Experimento | Entidade | Target histórico | Observado | Predição LightGBM | Baseline |
|---|---|---|---:|---:|---:|
| A | SBGR | 2023-01-01 | 581.0 | 685.5 | 623.9 |
| D-pax | SBCF→SBGR | 2023-01 | 64285.0 | 57779.7 | 54907.0 |

Em A a unidade é movimento no aeroporto-dia; em D-pax é passageiro pago na rota-mês.
As predições publicadas são arredondadas para a apresentação. O score do cabeçalho dos casos
é agrupado por horizontes, enquanto a curva usa h=1; essa distinção foi explicitada na interface.

## Por que os boosters congelados não podem refazer esse teste de 2023

A seleção produziu os valores acima antes de ver os targets de validação. Depois, os
boosters finais foram refitados com parte dos rótulos de 2023 disponíveis na primeira
origem do teste. Usá-los para prever 2023 produziria uma avaliação diferente e contaminada
por reuso de rótulos. A auditoria usa os Parquets de seleção salvos; confere apenas o hash
dos boosters finais. Não afirma ter reconstruído o treinamento histórico a partir de um
commit limpo: o manifest de treino registra alterações não commitadas.

## Controles de vazamento e o que não provam

Contratos fechados de features, cortes de histórico, stamps, vocabulário apenas no fitting,
purge, targets separados e testes que perturbam futuro reduzem caminhos de leakage.
Guards de baseline/modelo agora rejeitam features e targets do teste, inclusive datas
com fronteira configurável. Os testes passam sobre cenários sintéticos; não provam que
toda informação tinha a mesma versão publicada na época (faltam vintages).

A correção D distingue globalmente ausente de rota inativa. Ela muda o treino que uma
execução futura receberia, sem mudar arquivos congelados nem as métricas do v1. Não há
score de v2 corrigido para apresentar. Histogramas excluem y=0 quando usam erro relativo;
o WAPE, ao contrário, continua penalizando previsão positiva nesses zeros conhecidos.

## Calibração, risco e generalização

Um intervalo bootstrap de erro médio não informa um intervalo para o próximo voo.
Não existem intervalos preditivos conformais, cobertura temporal validada, calibração de
quantis ou garantia por rota nova. O evento secundário de alta ocupação é razão D-pax/D-seats,
não um modelo de preço: AP e Brier respondem a perguntas diferentes, e o Brier não foi
recomputado sem os artefatos de calibração. O limiar foi estimado no treino.

B é condicional à unidade operar, portanto não prevê cancelamento/abertura de rota.
D só considera universo elegível conhecido no cutoff, não descoberta de rotas inéditas.
Modelo A avalia grandes aeroportos e contagens, não lotação física da infraestrutura.
O desempenho agregado D não permite recomendar o h=6; o viés é material e a falha de treino
precisa de nova versão antes de adoção. MAE B não é Passenger Load Factor RPK/ASK.

## Caminho defensável para inferência futura — ainda pendente

1. Recuperar os quatro meses ou registrar sua ausência; publicar um novo dataset/versionamento.
2. Definir antes dos resultados protocolo para os zeros, universo, vintages, defasagem e horizontes.
3. Treinar em uma saída nova, persistir vocabulários/code/config/calibração e gerar comparação
   temporal sem promover v1 silenciosamente. Escolher modelos por tarefa/horizonte quando justificável.
4. Registrar como tratar o holdout parcialmente exposto; obter autorização antes de abrir targets.
   Um novo período prospectivo é mais forte que chamar esse teste de totalmente cego.
5. Só depois implementar extração point-in-time para novas origens e serving compatível com a
   identidade exata do modelo escolhido, inclusive baselines. Validar contrato e latência offline.
6. Monitorar drift, cobertura, viés, calibração/intervalos e mudanças de publicação. Sem preços
   observados, não criar endpoint de precificação ou alegar otimização de receita.

Nenhum desses passos de treino/holdout/serving/deploy foi executado nesta auditoria.
