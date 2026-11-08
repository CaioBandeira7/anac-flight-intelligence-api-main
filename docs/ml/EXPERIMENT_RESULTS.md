# Resultados dos experimentos e auditoria

Escopo: predições de seleção salvas, targets de **2023**. Não são teste 2024–2025 ou previsão atual.
Fonte imutável: `reports/models/module_{a,b,d}.json` e Parquets de validação em `data/features/v1`.
Reprodução atual: `scripts/audit_ml.py`; evidência estruturada: [audit.json](../../research/ml-showcase/results/audit.json).

## Métricas e regra de adoção histórica

WAPE = Σ|ŷ−y| / Σ|y|. MAE ponderado = Σ assentos×|ŷ−y| / Σ assentos.
A diferença é modelo − melhor baseline nas mesmas linhas; negativos favorecem o modelo.
O CI é de diferença pareada, não obtido subtraindo extremos de CIs individuais.
`beats_best_baseline` exige limite superior <0. As unidades abaixo são % para WAPE,
pontos percentuais (pp) de ocupação para MAE e pp da métrica para as diferenças.

| Target | Linhas comparáveis | LightGBM | Melhor baseline | Diferença | IC 95% da diferença | Decisão histórica |
|---|---:|---:|---:|---:|---|---|
| A | 36,500 | 10.095354 | 10.302566 | -0.207212 | [-0.844025; +0.346761] | baseline |
| B | 42,369 | 6.058023 | 6.541995 | -0.483973 | [-0.938230; -0.043803] | LightGBM |
| D-pax | 33,762 | 22.241909 | 25.308501 | -3.066592 | [-4.972356; -1.094918] | LightGBM |
| D-seats | 33,762 | 22.397056 | 25.729931 | -3.332875 | [-5.317340; -1.185566] | LightGBM |

### Por horizonte — não generalizar a decisão agregada

| Target | H | LightGBM | Melhor baseline desse H | Diferença | IC 95% |
|---|---:|---:|---|---:|---|
| A | 1 | 9.8742 | `pred_recent_weekday` (10.0919) | -0.2177 | [-0.9635; +0.4566] |
| A | 3 | 10.3165 | `pred_recent_weekday` (10.5132) | -0.1967 | [-0.8745; +0.4741] |
| B | 1 | 5.9891 | `pred_mean_12` (6.3298) | -0.3407 | [-0.8325; +0.1522] |
| B | 3 | 6.0918 | `pred_mean_12` (6.5553) | -0.4636 | [-0.9542; +0.0165] |
| B | 6 | 6.0944 | `pred_mean_12` (6.7459) | -0.6515 | [-1.0828; -0.2815] |
| D-pax | 1 | 18.7414 | `pred_pax_seasonal_trend` (24.0745) | -5.3331 | [-7.0586; -3.7230] |
| D-pax | 3 | 21.3114 | `pred_pax_seasonal_naive` (25.3481) | -4.0367 | [-5.9003; -2.0888] |
| D-pax | 6 | 26.7149 | `pred_pax_seasonal_naive` (25.0888) | +1.6262 | [-0.6148; +4.2514] |
| D-seats | 1 | 18.7105 | `pred_seats_seasonal_trend` (25.7176) | -7.0072 | [-7.9869; -5.9874] |
| D-seats | 3 | 21.4866 | `pred_seats_seasonal_naive` (25.7636) | -4.2770 | [-6.1089; -2.3997] |
| D-seats | 6 | 27.0399 | `pred_seats_seasonal_naive` (25.5269) | +1.5130 | [-0.9359; +4.6136] |

A não apresenta ganho conclusivo em h=1 ou h=3. B apresenta ganho agregado, mas os CIs de
h=1 e h=3 incluem zero; h=6 favorece o modelo. D ganha em h=1/h=3; h=6 tem estimativa de erro
maior que a regra anual e CI incluindo zero. Não concluir que foi provada inferioridade
no h=6 apenas pelo ponto estimado. A referência de h=1 D é a regra com tendência, embora
no agregado a melhor seja a anual simples.

## Segmentos e limites de cobertura

No diagnóstico B por natureza histórica do mercado: internacional tem MAE de **7,1229 pp**
contra **6,4980 pp** do baseline, enquanto o doméstico tem **5,8343 pp** contra **6,5512 pp**.
São estimativas de segmentos descritivos, sem CI pareado específico publicado no payload;
a adoção agregada não deve ser extrapolada à operação internacional. A classificação é a
feature histórica `id_is_international`, não uma nova geoclassificação territorial.

## Viés e distribuições

Volumes: Σ(ŷ−y)/Σ|y|. A: aproximadamente −2,01%; D-pax: −12,21%; D-seats: −11,78%.
Não atribuir causalmente o viés D a uma única falha: crescimento, transformação de nível,
árvores sem extrapolação direta, lacunas e mistura de horizontes são hipóteses.

B histórico usava `m.bias`, uma razão **não ponderada** de somas das frações de ocupação:
+0,038802% relativo. Isso não é um desvio em pp ponderado por assentos e pode mudar o sinal.
O KPI corrigido usa Σ assentos×(ŷ−y)/Σ assentos:
**-0.052152 pp**, IC [-1.050632; +0.923085] pp.

O campo histórico `bias` foi preservado no payload; `seat_weighted_bias` foi acrescentado,
com valores por horizonte, e usado no KPI B. Histograma B continua sendo distribuição
não ponderada das linhas em pontos: não confundir sua mediana com MAE/viés ponderado.

## Achados e correções

| Gravidade | Achado | Correção aplicada | Efeito sobre v1 |
|---|---|---|---|
| Alta | Loader D preenchia globalmente ausente como rota inativa | Excluir target_month ausente antes de preencher inatividade; aplicar também aos baselines | Não retreinado; 2023 permanece reproduzível, pois o ano não tem lacuna global |
| Alta | Guard de avaliação de baseline não rejeitava targets selados no arquivo | Validar targets e features contra a fronteira configurada, inclusive datas diárias | Impede uso futuro indevido; holdout não foi executado |
| Média | Average precision dependia da ordem de scores empatados | Agregar positivos/observações por limiar empatado; testes por cálculo manual | Altera levemente AP do baseline; não altera WAPE/MAE nem boosters |
| Média | Viés B era apresentado como se consistente com a ponderação principal | Novo viés ponderado em pp; fórmula e ressalva do campo antigo | Score principal preservado |
| Média | Exemplos h=1 exibiam score/ranking de horizontes agrupados | Explicitar ranking retrospectivo e score agrupado; remover sugestão de representatividade | Nenhuma previsão modificada |
| Média | Histogramas sem legenda visível e sem disclosure de zeros/caudas | Legenda, tooltips, contagem incluída, clipping/quantis explicados | Valores preservados |
| Média | Claim de payload sem dados de linha | Corrigir: agrega mais amostras limitadas de pares e séries de casos | Sem adicionar novos dados individuais |

- D-pax: 11,689 linhas de fitting e 11,689 de treino elegível atingidas pelo target desconhecido legado.
- D-seats: 11,692 linhas de fitting e 11,692 de treino elegível atingidas pelo target desconhecido legado.

Não há estimativa do ganho de um modelo corrigido: isso exigiria uma versão nova, com protocolo
fixado antes do teste. O score verificado descreve o modelo histórico, inclusive suas falhas.

### Evento secundário de alta ocupação

Não é um quinto booster: deriva a razão entre predições D-pax/D-seats e um limiar de treino.
O nome histórico `pr_auc` contém average precision (soma por saltos de recall), não integração
trapezoidal. O threshold relatado é 0,84545093; exige rota operada/assentos positivos.
- lightgbm: AP corrigida=0.6008393127; AP histórica=0.6008393127; Brier relatado=0.1977126325.
- baseline: AP corrigida=0.5890506146; AP histórica=0.5890443300; Brier relatado=0.1863496900.

Brier menor é melhor: o LightGBM piora essa métrica apesar do AP ligeiramente maior.
**Brier não foi reproduzido independentemente**: taxas da calibração e predições de seleção
sobre o treino não foram persistidas. LightGBM calibra na faixa de early stopping 2022;
o baseline usa o treino. Comparação não isola o efeito de ranking da estratégia de calibração.
Não transformar scores brutos de pressão em probabilidades de demanda nem recomendar preço.

## Força e limites da evidência

- 12 clusters mensais, bootstrap independente com reposição de meses, 2.000 draws, seed 42.
  Preserva dependência dentro do mês; **não é moving-block bootstrap** que preserva autocorrelação
  entre meses. Poucos clusters e um único ano tornam os intervalos frágeis.
- Baseline vencedor e decisão foram examinados no mesmo 2023; não há correção de multiplicidade,
  bootstrap aninhado da escolha ou demonstração em anos independentes.
- Dados são revisados, sem vintages as-of. Defasagem de 2 meses é hipótese registrada,
  não reconstituição comprovada da disponibilidade diária histórica.
- Teste 2024–2025 não foi pontuado, mas totais anuais foram vistos antes. Não é totalmente cego.
- Não há prova de generalização a rotas inéditas, aeroportos pequenos, outros anos ou novas políticas.
- Um refit final contém 2023 e não mede generalização nesse mesmo ano.

## O que foi executado nesta auditoria

601 verificações passaram: fórmulas NumPy independentes, reconciliação dos relatórios,
CIs/horizontes, agregações mensais respeitando arredondamento a 4 casas, chaves e hashes.
As guards e fórmulas têm testes sintéticos. Os únicos treinamentos executados são fixtures
sintéticas temporárias da suíte, nunca os quatro modelos de produção. Não foi feito refit
em dados reais, inferência sobre o holdout, rebuild de analytics, chamada LLM ou deploy.
Evidências de execuções anteriores em `reproduction.json` são históricas: após corrigir o
loader D, não afirmar refit bit-idêntico com a versão atual do código. Os arquivos originais
foram preservados. O Markdown/HTML/PDF do relatório receberam erratas explícitas sobre targets D, viés B
e refit histórico; as figuras e os scores anteriores foram preservados.
