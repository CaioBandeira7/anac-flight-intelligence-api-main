# Catálogo técnico dos modelos

Auditoria isolada a partir de `22a120a`. Evidência numérica: [audit.json](../../research/ml-showcase/results/audit.json).
Escopo atual: **4 regressores LightGBM, 3 módulos (A/B/D)**. São 3/3/2/2 regras de baseline,
respectivamente (10 previsões de referência para os quatro targets). Há **zero modelo C treinado**.
Não confundir famílias, targets, baselines, boosters de seleção e boosters finais refitados.

## Dados e definições

Fonte: snapshot `anac_brazil.csv`, processado em `flights`, 22.120.241 registros, 308 meses
entre 2000-01 e 2025-12; o corte de features supervisionadas termina em 2023-12.
A auditoria não abriu targets de 2024–2025. `dataset_digest` registrado: `14fa41725d655b59`.
O digest histórico usa nomes/tamanhos, não hash de conteúdo: rastreabilidade incompleta.
Foram acrescentados hashes SHA-256 dos arquivos efetivamente auditados, sem alterar a fonte.

A: unidade aeroporto × dia, top 50 selecionados por movimentos nos 730 dias anteriores ao cutoff.
O painel soma endpoints de registros efetivamente operados (`pl.len()`), por datas reais,
com fallback à referência quando datas são ausentes/incoerentes. Não é atraso, fila ou capacidade
física; não assumir equivalência com uma soma arbitrária de `nr_decolagem` de outra camada.
Um auto-loop gera dois movimentos; uma viagem pode aparecer em vários aeroportos.

B/D: unidade companhia × origem × destino × mês (B) ou rota direcionada × mês (D).
Escopo: remove duplicatas, sem decolagem, improdutivos, distância zero, mesma origem/destino,
sem passageiros pagos, sem assentos e ocupação por voo >1,5. Valores entre 1 e 1,5 permanecem.
Elegibilidade usa ≥500 assentos/mês em média nos 12 meses conhecidos e atividade recente,
definida com histórico disponível até o cutoff; não seleciona unidades pelo target.
B avalia apenas unidades que operaram no target. D inclui inatividade conhecida como zero.
A ocupação B (`load_factor`) é **Σ passageiros pagos / Σ assentos**; não é RPK/ASK.
D estima demanda atendida e oferta operada, não demanda reprimida, tarifas ou lucro.

Lacunas globais: **2015-08, 2016-02, 2018-07, 2020-08**. A distinção correto/legado
é essencial: lags preservavam a ausência, mas o loader D v1 zerava os targets ausentes.
A correção atual exclui esses meses antes do preenchimento de inatividade; v1 não foi retreinado.

## Algoritmo e treinamento

`src/anac/models/train.py` e `configs/models.toml`: GBDT LightGBM, regressão L1,
uma configuração conservadora declarada, sem busca de hiperparâmetros registrada.
A escolha é defensável por dados tabulares, interações, categorias nativas e custo;
o repositório não comprova superioridade contra redes neurais, XGBoost ou todos os métodos possíveis.

Para volumes: rótulo `y / nível`, peso `nível`, de modo que
`nível × |y/nível − p| = |y − nível×p|`. A otimização L1 do numerador está alinhada ao WAPE,
cujo denominador é fixo na amostra. Isso não significa que cada folha otimiza WAPE separado.
A escala é `hist_level_56` (A), `hist_pax_mean_12` (D-pax) e `hist_seats_mean_12` (D-seats).
B usa o target diretamente, com assentos observados como pesos de treino/avaliação,
não como feature do mês futuro. Predições são limitadas inferiormente a zero; B não é clipado em 1.
Categorias usam vocabulário ajustado no fitting; desconhecidas tornam-se missing.
Absolutos de data/cutoff e stamps são excluídos do booster; horizonte e distância são mantidos.

Treino elegível: targets de 2013 em diante até `2023-01 − distance`.
Fitting de seleção: `target_month <= 2022-01 − distance`; stopping: targets de 2022.
`distance = horizon + 2` com a defasagem publicada assumida. As fronteiras têm purge por horizonte.
2023 é validação temporal com múltiplas origens/horizontes e um modelo de seleção fixo,
não um rolling-refit com vários folds independentes. Não há seleção no holdout nesta auditoria.

Depois da seleção do número de árvores, os boosters finais foram refitados em dados disponíveis
até a primeira origem do teste, incluindo partes de 2023, e congelados. **Não se pode usar esses
boosters finais para reproduzir o score de validação de 2023**: usar as predições de seleção salvas.
A última referência global declarada nos manifests é 2023-10; a restrição é por horizonte
(h=1: outubro; h=3: agosto; h=6: maio) e depende da disponibilidade efetiva dos rótulos.
O campo de metadata foi calculado para a configuração padrão; revalidá-lo ao mudar a defasagem.

### Hiperparâmetros exatos

```json
{
  "objective": "l1",
  "metric": "l1",
  "learning_rate": 0.03,
  "num_leaves": 31,
  "min_data_in_leaf": 200,
  "feature_fraction": 0.8,
  "bagging_fraction": 0.8,
  "bagging_freq": 1,
  "lambda_l2": 5.0,
  "cat_smooth": 20.0,
  "min_data_per_group": 200,
  "max_cat_threshold": 32,
  "seed": 42,
  "deterministic": true,
  "force_col_wise": true,
  "num_threads": 4,
  "verbosity": -1
}
```

Máximo 3.000 rounds; early stopping de 50 rounds. Escolha de rounds em 2022; nunca sobre 2023.

| Target | Features numéricas/categóricas | Fitting registrado v1 | Stopping registrado | Árvores | Refit final registrado |
|---|---|---:|---:|---:|---:|
| A | 20/1 | 306,068 | 27,350 | 98 | 379,068 |
| B | 39/3 | 366,818 | 23,448 | 46 | 442,733 |
| D-pax | 36/2 | 291,026 | 18,087 | 395 | 350,518 |
| D-seats | 36/2 | 291,104 | 18,099 | 243 | 350,614 |

As contagens são históricas de v1; o loader corrigido exclui targets D antes usados como zero.
Não foram recalculados scores de um novo modelo. Hashes dos quatro `.txt` conferem com manifests;
vocabulários receberam hash nesta auditoria, mas o manifest original não os autenticava.
O treinamento registra commit `210b039` com `tracked_changes: true`: não há uma fotografia Git
limpa suficiente para reconstruir inequivocamente todo o código original a partir desse commit.

## Contrato completo das features efetivamente usadas

Fonte: `contracts.py`, seleção por `model_columns`, ordem comparada com o manifest congelado.
Médias históricas B/D: janelas de calendário de 3/6/12 meses, divididas pelo número de meses
globalmente conhecidos; um mês conhecido sem operação é zero. Não são as últimas N observações
não vazias. Desvio-padrão é entre meses operados observados. `id_km` é mediana no histórico
limitado a 40 meses, e não distância obtida da geometria. Lags são relativos ao target e
validados contra o cutoff. As features de rede leem todas as unidades conhecidas no corte.
Stamps/cutoffs/identificadores absolutos fora da seleção não são preditores.

### Módulo A

| Feature | Tipo | Origem | Definição / transformação |
|---|---|---|---|
| `horizon` | Int32 | timing | Months from origin to target |
| `distance` | Int32 | timing | Months from cutoff to target |
| `distance_days` | Int32 | timing | Days from cutoff to target |
| `cal_day_of_week` | Int8 | calendar | 0 is Monday |
| `cal_day_of_month` | Int8 | calendar | Day of the month |
| `cal_month` | Int8 | calendar | Calendar month |
| `cal_week_of_year` | Int8 | calendar | ISO week |
| `cal_is_weekend` | Boolean | calendar | Saturday or Sunday |
| `cal_is_holiday` | Boolean | calendar | National holiday |
| `cal_is_carnival` | Boolean | calendar | Carnival Monday or Tuesday |
| `cal_is_day_before_special` | Boolean | calendar | Day before a holiday or Carnival |
| `cal_is_day_after_special` | Boolean | calendar | Day after a holiday or Carnival |
| `cal_is_school_vacation` | Boolean | calendar | January, July or December |
| `id_rank_24m` | Int32 | identity | Rank by movements, 24 months to cutoff |
| `hist_lag_364` | Float64 | history | Movements 364 days before target (null if unknown) |
| `hist_lag_728` | Float64 | history | Movements 728 days before target (null if unknown) |
| `hist_same_dow_mean_8w` | Float64 | history | Mean on the target's weekday, 8 weeks to cutoff |
| `hist_level_28` | Float64 | history | Mean daily movements, 28 days to cutoff |
| `hist_level_56` | Float64 | history | Mean daily movements, 56 days to cutoff |
| `hist_yoy_56` | Float64 | history | Last 56 days over the same days a year earlier |
| `airport` | String | identity | Airport ICAO |

### Módulo B

| Feature | Tipo | Origem | Definição / transformação |
|---|---|---|---|
| `horizon` | Int32 | timing | Months from origin to target |
| `distance` | Int32 | timing | Months from cutoff to target |
| `cal_month` | Int8 | calendar | Calendar month |
| `cal_days_in_month` | Int8 | calendar | Days in the month |
| `cal_weekend_days` | Int8 | calendar | Saturdays and Sundays |
| `cal_holidays` | Int8 | calendar | National holidays |
| `cal_has_carnival` | Boolean | calendar | Month contains Carnival |
| `cal_is_school_vacation` | Boolean | calendar | January, July or December |
| `id_km` | Float64 | identity | Median route distance up to cutoff |
| `id_is_international` | Boolean | identity | Crosses the border |
| `hist_route_lf_3` | Float64 | history | Load factor of the route across carriers, 3 months to cutoff |
| `hist_carrier_lf_3` | Float64 | history | Load factor of the carrier across routes, 3 months to cutoff |
| `hist_carrier_seat_share_3` | Float64 | history | Carrier share of the route's seats, 3 months to cutoff |
| `hist_seats_mean_3` | Float64 | history | Mean monthly seats, 3 known months to cutoff |
| `hist_seats_mean_6` | Float64 | history | Mean monthly seats, 6 known months to cutoff |
| `hist_seats_mean_12` | Float64 | history | Mean monthly seats, 12 known months to cutoff |
| `hist_pax_mean_3` | Float64 | history | Mean monthly paid passengers, 3 known months to cutoff |
| `hist_pax_mean_6` | Float64 | history | Mean monthly paid passengers, 6 known months to cutoff |
| `hist_pax_mean_12` | Float64 | history | Mean monthly paid passengers, 12 known months to cutoff |
| `hist_flights_mean_3` | Float64 | history | Mean monthly flights, 3 known months to cutoff |
| `hist_seats_per_flight_3` | Float64 | history | Seats per flight, 3 months to cutoff |
| `hist_lf_3` | Float64 | history | Seat-weighted paid load factor, 3 months to cutoff |
| `hist_lf_6` | Float64 | history | Seat-weighted paid load factor, 6 months to cutoff |
| `hist_lf_12` | Float64 | history | Seat-weighted paid load factor, 12 months to cutoff |
| `hist_lf_std_12` | Float64 | history | Standard deviation of monthly load factor, 12 months to cutoff |
| `hist_yoy_pax` | Float64 | history | Paid passengers, last 3 months over the same months a year earlier |
| `hist_yoy_seats` | Float64 | history | Seats, last 3 months over the same months a year earlier |
| `hist_pax_lag_12` | Float64 | history | Paid passengers in month T-12 (0 if not flown, null if unknown) |
| `hist_seats_lag_12` | Float64 | history | Seats in target month minus 12 (0 if not operated, null if unknown) |
| `hist_lf_lag_12` | Float64 | history | Load factor in target month minus 12 (null if not operated or unknown) |
| `hist_pax_lag_24` | Float64 | history | Paid passengers in month T-24 (0 if not flown, null if unknown) |
| `hist_seats_lag_24` | Float64 | history | Seats in target month minus 24 (0 if not operated, null if unknown) |
| `hist_lf_lag_24` | Float64 | history | Load factor in target month minus 24 (null if not operated or unknown) |
| `hist_origin_lf_3` | Float64 | history | Load factor of the origin airport, 3 months to cutoff |
| `hist_destination_lf_3` | Float64 | history | Load factor of the destination airport, 3 months to cutoff |
| `hist_carriers_on_route_3` | Float64 | history | Carriers on the route, 3 months to cutoff |
| `hist_months_observed_12` | Int32 | history | Months with flights among the 12 to cutoff |
| `hist_unknown_months_12` | Int32 | history | Months with no data at all among the 12 to cutoff |
| `hist_months_since_first` | Int32 | history | Months between first flight and cutoff |
| `origin` | String | identity | Origin ICAO |
| `destination` | String | identity | Destination ICAO |
| `carrier` | String | identity | Carrier ICAO |

### Módulo D — compartilhado por pax e seats

| Feature | Tipo | Origem | Definição / transformação |
|---|---|---|---|
| `horizon` | Int32 | timing | Months from origin to target |
| `distance` | Int32 | timing | Months from cutoff to target |
| `cal_month` | Int8 | calendar | Calendar month |
| `cal_days_in_month` | Int8 | calendar | Days in the month |
| `cal_weekend_days` | Int8 | calendar | Saturdays and Sundays |
| `cal_holidays` | Int8 | calendar | National holidays |
| `cal_has_carnival` | Boolean | calendar | Month contains Carnival |
| `cal_is_school_vacation` | Boolean | calendar | January, July or December |
| `id_km` | Float64 | identity | Median route distance up to cutoff |
| `id_is_international` | Boolean | identity | Crosses the border |
| `hist_seats_mean_3` | Float64 | history | Mean monthly seats, 3 known months to cutoff |
| `hist_seats_mean_6` | Float64 | history | Mean monthly seats, 6 known months to cutoff |
| `hist_seats_mean_12` | Float64 | history | Mean monthly seats, 12 known months to cutoff |
| `hist_pax_mean_3` | Float64 | history | Mean monthly paid passengers, 3 known months to cutoff |
| `hist_pax_mean_6` | Float64 | history | Mean monthly paid passengers, 6 known months to cutoff |
| `hist_pax_mean_12` | Float64 | history | Mean monthly paid passengers, 12 known months to cutoff |
| `hist_flights_mean_3` | Float64 | history | Mean monthly flights, 3 known months to cutoff |
| `hist_seats_per_flight_3` | Float64 | history | Seats per flight, 3 months to cutoff |
| `hist_lf_3` | Float64 | history | Seat-weighted paid load factor, 3 months to cutoff |
| `hist_lf_6` | Float64 | history | Seat-weighted paid load factor, 6 months to cutoff |
| `hist_lf_12` | Float64 | history | Seat-weighted paid load factor, 12 months to cutoff |
| `hist_lf_std_12` | Float64 | history | Standard deviation of monthly load factor, 12 months to cutoff |
| `hist_yoy_pax` | Float64 | history | Paid passengers, last 3 months over the same months a year earlier |
| `hist_yoy_seats` | Float64 | history | Seats, last 3 months over the same months a year earlier |
| `hist_pax_lag_12` | Float64 | history | Paid passengers in month T-12 (0 if not flown, null if unknown) |
| `hist_seats_lag_12` | Float64 | history | Seats in target month minus 12 (0 if not operated, null if unknown) |
| `hist_lf_lag_12` | Float64 | history | Load factor in target month minus 12 (null if not operated or unknown) |
| `hist_pax_lag_24` | Float64 | history | Paid passengers in month T-24 (0 if not flown, null if unknown) |
| `hist_seats_lag_24` | Float64 | history | Seats in target month minus 24 (0 if not operated, null if unknown) |
| `hist_lf_lag_24` | Float64 | history | Load factor in target month minus 24 (null if not operated or unknown) |
| `hist_origin_lf_3` | Float64 | history | Load factor of the origin airport, 3 months to cutoff |
| `hist_destination_lf_3` | Float64 | history | Load factor of the destination airport, 3 months to cutoff |
| `hist_carriers_on_route_3` | Float64 | history | Carriers on the route, 3 months to cutoff |
| `hist_months_observed_12` | Int32 | history | Months with flights among the 12 to cutoff |
| `hist_unknown_months_12` | Int32 | history | Months with no data at all among the 12 to cutoff |
| `hist_months_since_first` | Int32 | history | Months between first flight and cutoff |
| `origin` | String | identity | Origin ICAO |
| `destination` | String | identity | Destination ICAO |

## Baselines e escolhas

A: mesmo dia da semana há 364 dias; esse lag multiplicado por tendência YoY 56 dias;
média do mesmo dia da semana em 8 semanas. Lags desconhecidos usam fallback recente.
B: mesmo mês do ano anterior com fallback à média histórica; média ponderada de 12 meses;
média ponderada de 3 meses. D: mesmo mês do ano anterior e lag anual com tendência
limitada a [0,5;2]; fallback à média recente quando a tendência/lag não é utilizável.
A melhor regra é escolhida no conjunto comparável de 2023; não é sempre a melhor em cada horizonte.
O registro da API marca seleção no agregado por módulo; isso não valida cada horizonte.

## Módulo C e legados: não são resultados implantados

C tem avaliação de viabilidade, não booster/baseline treinado. O target candidato é bagagem
despachada total por passageiro pago. `reports/baggage/module_c_assessment.json` cobre 2018–2022:
AZU/TAM/PTB satisfazem o gate, cobrindo cerca de 61,5% dos passageiros domésticos. Gol falha;
a mudança de método do gate após resultados limita a força dessa evidência. Não apresentar
isso como AUC, previsão de bagagem individual ou recomendação de cobrança.

| Código legado, somente leitura | Algoritmo/target proposto | Evidência e restrição |
|---|---|---|
| `03_modelo_aeroporto.py` | LSTM + atenção temporal, movimento/congestionamento agregado | Código v1; sem artefato/score auditado no catálogo atual. Movimentos não medem congestionamento. |
| `04_modelo_assentos.py` | FT-Transformer, taxa/bucket de ocupação | Código v1; não é o LightGBM B. Agregações históricas devem ser auditadas contra o cutoff antes de reutilização. |
| `05_modelos_preco_bagagem.py`, preço | MLP com embeddings, `pressao_preco` | Proxy construído de ocupação/tendência em `02_feature_engineering.py`; não existem tarifas observadas. Não defender precificação real. |
| mesmo arquivo, bagagem | LightGBM + DNN/stacking, flag de excesso | Split aleatório estratificado e estatísticas globais ameaçam avaliação temporal; sem métricas verificadas nesta auditoria. |

Esses scripts não foram executados nem editados. O serviço atual usa `src/anac`, não as rotas
de `06_api.py`. Sua existência não comprova treinamento de redes neurais nem qualidade preditiva.
