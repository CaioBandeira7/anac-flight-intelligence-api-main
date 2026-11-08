"""Build the six technical audit documents from verified local evidence and authored explanations."""

from __future__ import annotations

import json
from pathlib import Path

from anac.features.contracts import CONTRACTS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/ml"
EVIDENCE = ROOT / "research/ml-showcase/results/audit.json"
TASKS = {
    "a": ("A", "Movimentos aeroportuários", "movements"),
    "b": ("B", "Ocupação paga por assentos", "load_factor"),
    "d_pax": ("D-pax", "Passageiros pagos transportados", "pax"),
    "d_seats": ("D-seats", "Assentos operados", "seats"),
}


def write(name: str, text: str) -> None:
    (OUT / name).write_text(text.strip() + "\n", encoding="utf-8")


def model_catalog(v: dict) -> None:
    text = """# Catálogo técnico dos modelos

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

"""
    params = v["modules"]["a"]["frozen_manifest"]["params"]
    text += "```json\n" + json.dumps(params, indent=2) + "\n```\n\n"
    text += "Máximo 3.000 rounds; early stopping de 50 rounds. Escolha de rounds em 2022; nunca sobre 2023.\n\n"
    text += "| Target | Features numéricas/categóricas | Fitting registrado v1 | Stopping registrado | Árvores | Refit final registrado |\n|---|---|---:|---:|---:|---:|\n"
    for key, (label, _, target) in TASKS.items():
        t = v["tasks"][key]
        mod = t["module"]
        m = v["modules"][mod]["frozen_manifest"]["models"][target]
        text += f"| {label} | {len(m['numeric'])}/{len(m['categorical'])} | {t['selection_fit_rows_recorded']:,} | {t['stopping_rows_recorded']:,} | {t['rounds']} | {m['rows']:,} |\n"
    text += """
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

"""
    for module in ["a", "b", "d"]:
        text += (
            f"### Módulo {module.upper()}"
            + (" — compartilhado por pax e seats" if module == "d" else "")
            + "\n\n"
        )
        text += "| Feature | Tipo | Origem | Definição / transformação |\n|---|---|---|---|\n"
        for info in v["modules"][module]["features"]:
            spec = next(s for s in CONTRACTS[module].features if s.name == info["name"])
            text += f"| `{spec.name}` | {spec.dtype.__name__} | {spec.source.value} | {spec.description} |\n"
        text += "\n"
    text += """## Baselines e escolhas

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
"""
    write("MODEL_CATALOG.md", text)


def experiment_results(v: dict) -> None:
    text = """# Resultados dos experimentos e auditoria

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
"""
    for key, (label, _, _) in TASKS.items():
        t = v["tasks"][key]
        m = t["metrics"]
        d = m["difference_vs_best_baseline"]
        b = m["baselines"][m["best_baseline"]]["value"]
        text += f"| {label} | {t['rows']:,} | {100 * m['lightgbm']['value']:.6f} | {100 * b:.6f} | {100 * d['value']:+.6f} | [{100 * d['ci95'][0]:+.6f}; {100 * d['ci95'][1]:+.6f}] | {'LightGBM' if m['beats_best_baseline'] else 'baseline'} |\n"
    text += "\n### Por horizonte — não generalizar a decisão agregada\n\n| Target | H | LightGBM | Melhor baseline desse H | Diferença | IC 95% |\n|---|---:|---:|---|---:|---|\n"
    for key, (label, _, _) in TASKS.items():
        for h, m in v["tasks"][key]["metrics"]["by_horizon"].items():
            text += f"| {label} | {h} | {100 * m['lightgbm']:.4f} | `{m['best_baseline']}` ({100 * m['best_baseline_value']:.4f}) | {100 * m['difference']:+.4f} | [{100 * m['ci95'][0]:+.4f}; {100 * m['ci95'][1]:+.4f}] |\n"
    text += """
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
"""
    b = v["tasks"]["b"]["seat_weighted_bias"]
    text += f"**{100 * b['value']:+.6f} pp**, IC [{100 * b['ci95'][0]:+.6f}; {100 * b['ci95'][1]:+.6f}] pp.\n\n"
    text += """O campo histórico `bias` foi preservado no payload; `seat_weighted_bias` foi acrescentado,
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

"""
    for key in ["d_pax", "d_seats"]:
        t = v["tasks"][key]
        text += f"- {TASKS[key][0]}: {t['legacy_unknown_fit_rows']:,} linhas de fitting e {t['legacy_unknown_train_rows']:,} de treino elegível atingidas pelo target desconhecido legado.\n"
    text += """
Não há estimativa do ganho de um modelo corrigido: isso exigiria uma versão nova, com protocolo
fixado antes do teste. O score verificado descreve o modelo histórico, inclusive suas falhas.

### Evento secundário de alta ocupação

Não é um quinto booster: deriva a razão entre predições D-pax/D-seats e um limiar de treino.
O nome histórico `pr_auc` contém average precision (soma por saltos de recall), não integração
trapezoidal. O threshold relatado é 0,84545093; exige rota operada/assentos positivos.
"""
    sec = v["secondary_pressure"]
    for name in ["lightgbm", "baseline"]:
        m = sec[name]
        text += f"- {name}: AP corrigida={m['average_precision_tie_corrected']:.10f}; AP histórica={m['reported_legacy_pr_auc']:.10f}; Brier relatado={m['reported_brier']:.10f}.\n"
    text += """
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

"""
    text += f"{v['check_count']} verificações passaram: fórmulas NumPy independentes, reconciliação dos relatórios,\nCIs/horizontes, agregações mensais respeitando arredondamento a 4 casas, chaves e hashes.\n"
    text += """As guards e fórmulas têm testes sintéticos. Os únicos treinamentos executados são fixtures
sintéticas temporárias da suíte, nunca os quatro modelos de produção. Não foi feito refit
em dados reais, inferência sobre o holdout, rebuild de analytics, chamada LLM ou deploy.
Evidências de execuções anteriores em `reproduction.json` são históricas: após corrigir o
loader D, não afirmar refit bit-idêntico com a versão atual do código. Os arquivos originais
foram preservados. O Markdown/HTML/PDF do relatório receberam erratas explícitas sobre targets D, viés B
e refit histórico; as figuras e os scores anteriores foram preservados.
"""
    write("EXPERIMENT_RESULTS.md", text)


def visualization_catalog(v: dict) -> None:
    payload = json.loads((ROOT / "web/public/ml/showcase.json").read_text(encoding="utf-8"))
    entries = []
    source = "`web/public/ml/showcase.json` ← predições/targets 2023 e `analysis.py`"

    def add(
        identifier, name, location, task, purpose, axes, data, interpretation, conclusion, limits
    ):
        entries.append(
            {
                "id": identifier,
                "name": name,
                "location": location,
                "task": task,
                "purpose": purpose,
                "axes": axes,
                "data": data,
                "interpretation": interpretation,
                "conclusion": conclusion,
                "limits": limits,
            }
        )

    for key, (label, _title, _) in TASKS.items():
        task = payload["tasks"][key]
        ratio = key == "b"
        value = "ocupação paga, fração exibida em %" if ratio else task["unit"]
        error = "MAE ponderado por assentos, pp" if ratio else "WAPE, %"
        default = "Lower is better; cor do modelo=chart-1/azul, baseline=muted/cinza; atual=ink; tokens DAY/NIGHT."
        families = {
            "monthly": (
                "Actual vs predicted, by target month",
                "TaskView / LinesChart",
                "Comparar nível observado, previsão de seleção e referência.",
                f"X: janeiro a dezembro de 2023. Y: {value}. Atual, LightGBM e melhor baseline global.",
                "monthly, filtrado por horizon; B usa assentos observados como pesos de todas as séries.",
                "A proximidade de totais/médias avalia nível agregado, não igualdade por unidade.",
                "Revela desvios temporais e de nível do experimento selecionado.",
                "Cancelamentos de erro podem ocultar falhas de rota/dia. Só este gráfico acompanha o seletor de horizonte; comparação fixa no melhor baseline agregado.",
            ),
            "volume": (
                "Error by traffic volume",
                "TaskView / LinesChart",
                "Inspecionar heterogeneidade do erro por tamanho histórico.",
                f"X: decis 1–10 da feature SIZE conhecida no cutoff. Y: {error}, modelo e baseline.",
                "by_volume_decile; níveis A=hist_level_56, B=hist_seats_mean_12, D=hist_pax/seats_mean_12.",
                "Agrupa observações por feature histórica; limites dos decis são estimados em 2023.",
                "Sustenta diferenças descritivas de dificuldade entre estratos observados.",
                "Não é WAPE por número de unidades nem ranking futuro. Decis não são limiares fixados no treino; os horizontes estão agrupados.",
            ),
            "entity": (
                f"Largest units, by {'airport (ICAO)' if key == 'a' else 'carrier' if ratio else 'directed route'}",
                "TaskView / PairBars",
                "Comparar modelo e regra nas maiores entidades observadas.",
                f"Entidade no eixo categórico; comprimento horizontal= {error}. Azul modelo, cinza baseline.",
                "by_entity[:10], agrupado por aeroporto A, companhia B ou rota D; tamanho por volume observado em 2023.",
                "Ranking é retrospectivo e os erros são recalculados sobre as linhas de cada entidade.",
                "Mostra onde o modelo erra mais/menos entre grandes entidades efetivamente avaliadas.",
                "B agrega rotas de cada companhia; não é erro por companhia×rota individual. Não representa entidades pequenas nem fatia de mercado; horizontes repetem targets.",
            ),
            "residuals": (
                "Residuals",
                "TaskView / Histogram",
                "Inspecionar assimetria, dispersão e caudas dos erros assinados.",
                "X: (predito−real)×100 em pp para B, ou (predito−real)/real para volumes. Y: número não ponderado de linhas; duas cores sobrepostas.",
                f"residuals; {task['residuals']['rows']:,} linhas incluídas de {task['rows']:,}; bins fixos ±30 pp B ou ±100% volumes.",
                "Positivo é sobreprevisão. Caudas são acumuladas no primeiro/último bin; p10/p50/p90 usam resíduos sem clipping.",
                "Sustenta descrição empírica de sinais e caudas na amostra incluída.",
                "Volumes zero ficam fora do erro relativo; distribuição não ponderada pode discordar de WAPE/MAE ponderado. p10–p90 não é intervalo preditivo futuro.",
            ),
            "scatter": (
                "Actual vs predicted, row level",
                "TaskView / Scatter",
                "Ver alinhamento entre observações e predições pontuais.",
                f"X: observado, Y: LightGBM, na unidade {value}; diagonal y=x. Log nos dois eixos de volumes; linear para B.",
                "scatter: até 400 pares de validação h=1, amostra com seed 11; contém informação de linhas, embora limitada.",
                "Abaixo da diagonal é subprevisão. Amostra é diagnóstica; score usa todas as linhas comparáveis.",
                "Sustenta o padrão visual de dispersão da amostra, sem estimar acurácia por densidade aparente.",
                "Pares não positivos são removidos nos eixos log; pontos sobrepostos escondem densidade. Sem baseline ou intervalo de previsão por ponto.",
            ),
            "gain": (
                "What the trees split on",
                "TaskView / BarList",
                "Descrever como o booster de seleção distribuiu ganho de splits.",
                "Y: nome da feature; X/comprimento: fração do ganho total, exibida em %; top 10.",
                "top_features_by_gain dos reports/models; não recalculado do booster final refitado.",
                "É importância interna do fitting, enviesável por cardinalidade e correlação.",
                "Permite verificar se o modelo usa níveis, calendário e identidades plausíveis.",
                "Não é SHAP, efeito causal, contribuição de uma predição nem permutation importance em validação. Top 10 não soma necessariamente 100%.",
            ),
        }
        for family, (
            name,
            location,
            purpose,
            axes,
            data,
            interpretation,
            conclusion,
            limits,
        ) in families.items():
            add(
                f"web-{key}-{family}",
                name,
                "`web/components/dashboard/ml-showcase.tsx` " + location,
                label,
                purpose,
                axes,
                source + "; " + data,
                interpretation + " " + default,
                conclusion,
                limits,
            )
        add(
            f"web-{key}-horizon-table",
            "Error by horizon",
            "`ml-showcase.tsx` / DataTable",
            label,
            "Comparar todas as regras e o viés em cada horizonte.",
            f"Linhas: horizonte origem→target; colunas: {error} de cada método e viés assinado.",
            source
            + "; by_horizon. Viés B corrigido usa seat_weighted_bias_model; demais usam bias_model.",
            "Selecionar o menor ponto não demonstra significância. Os CIs por horizonte estão em EXPERIMENT_RESULTS.",
            "A e B h=1/h=3 não têm ganho conclusivo; D h=6 não demonstra superioridade.",
            "A regra global pode mudar por horizonte. Tabela não segue o seletor do gráfico mensal.",
        )
        for stat, explanation in [
            ("model", "Erro do LightGBM no conjunto comparável."),
            ("baseline", "Menor erro entre baselines no mesmo conjunto."),
            ("difference", "Erro modelo menos melhor baseline; diferença pareada."),
            ("bias", "Erro assinado; B ponderado por assentos em pp, volumes relativos em %."),
        ]:
            add(
                f"web-{key}-kpi-{stat}",
                stat + " KPI",
                "`ml-showcase.tsx` / StatTile",
                label,
                explanation,
                "Sem eixos; número e unidade explícitos. CIs de erro quando exibidos.",
                source,
                "Valores agregam horizontes e linhas comparáveis; não são métricas de teste.",
                "A mantém baseline; B/D têm evidência histórica agregada, sujeita às ressalvas auditadas.",
                "Um percentual de erro não é accuracy; a decisão histórica não valida o modelo corrigido futuro.",
            )
        if task["examples"]:
            add(
                f"web-{key}-examples",
                "Retrospective hits and misses",
                "`ml-showcase.tsx` / ExampleChart → LinesChart",
                label,
                "Inspecionar dois extremos escolhidos retrospectivamente, sem representar toda a população.",
                f"X: dia de 2023 para A ou mês para D-pax. Y: {value}; atual, modelo, regra.",
                source
                + "; examples.best/worst. Seleção por erro agrupado entre top 10 aeroportos ou top 20 rotas; séries apenas h=1.",
                "O score escrito pertence ao agrupamento de horizontes usado no ranking, não só à curva h=1.",
                "Ilustra falhas/acertos concretos nas entidades escolhidas.",
                "Cherry-picking descritivo explicitado; não é comparação prospectiva, teste de significância ou amostra representativa.",
            )
        # Every existing paper figure is also inventoried separately from its web equivalent.
        figure_map = {
            "monthly": "actual_vs_predicted_monthly",
            "scatter": "scatter",
            "residuals": "residuals",
            "horizon-table": "by_horizon",
            "volume": "by_volume",
            "entity": "by_entity",
            "gain": "feature_gain",
            "monthly-error": "error_by_month",
        }
        for family, suffix in figure_map.items():
            if family == "horizon-table":
                purpose = "Comparar erros por horizonte em barras agrupadas."
                axes = f"X: h=1/3 ou 1/3/6; Y: {error}; uma barra por método."
                interpretation = (
                    "Mesmo conjunto de linhas por método; só estimativas pontuais no gráfico."
                )
                conclusion = (
                    "Revela heterogeneidade por horizonte, sem dispensar os intervalos pareados."
                )
                limits = "Não declarar superioridade apenas pelo menor comprimento; não há CI de diferença desenhado."
                data = "by_horizon, todas as regras."
            elif family == "monthly-error":
                purpose = "Examinar a variação do erro de unidade por target-month."
                axes = (
                    f"X: mês de 2023; Y: {error}. Painéis por horizonte, curvas modelo e baseline."
                )
                interpretation = "Erro calculado antes de agregar; não é erro entre os totais do gráfico de nível."
                conclusion = "Mostra sazonalidade do desempenho no ano avaliado."
                limits = "Doze pontos por horizonte não provam um padrão anual generalizável; compara a regra global."
                data = "monthly.model_error/baseline_error."
            else:
                _, _, purpose, axes, data, interpretation, conclusion, limits = families[family]
                if family == "scatter":
                    data = "scatter_sample com n≤4.000 e seed 7; distingue-se dos 400 pares seed 11 da web."
                if family == "entity":
                    data = "by_entity: até 20 entidades, em vez das 10 da web."
            filename = f"{key}_{suffix}"
            add(
                "paper-" + filename,
                filename,
                f"`research/ml-showcase/figures/{filename}.png` (+ `.svg`)",
                label,
                purpose,
                axes,
                "`analysis.py` e validation_frame → predições 2023; " + data,
                interpretation,
                conclusion,
                limits
                + " O PDF/figura v1 preservado pode usar nomenclatura antiga; conferir erratas da auditoria.",
            )
        if task["examples"]:
            suffix = "examples_daily" if key == "a" else "examples"
            filename = f"{key}_{suffix}"
            add(
                "paper-" + filename,
                filename,
                f"`research/ml-showcase/figures/{filename}.png` (+ `.svg`)",
                label,
                "Mesmos extremos da web em painéis estáticos.",
                f"X: dia/mês de 2023, h=1; Y: {value}. Três séries identificadas na legenda.",
                "`analysis.py::fig_examples_a/fig_examples_routes`, seleção retrospectiva pelos erros agrupados.",
                "Título histórico associa WAPE agrupado a uma curva h=1: a distinção é obrigatória nesta leitura.",
                "Permite inspecionar visualmente entidades escolhidas após a avaliação.",
                "Casos extremos não são representativos. Figuras históricas mantidas; errata documenta o escopo do score.",
            )
    add(
        "paper-overview_model_vs_baseline",
        "overview_model_vs_baseline",
        "`figures/overview_model_vs_baseline.{png,svg}`",
        "A/B/D-pax/D-seats",
        "Comparar cada target com seu próprio baseline.",
        "Painéis por target; erro principal na unidade própria e anotações de decisão/intervalo.",
        "`analysis.py::fig_overview` e reports/models.",
        "Comparação válida dentro de cada tarefa; MAE de ocupação e WAPE não compartilham semântica.",
        "A não supera conclusivamente a referência; B/D têm ganho agregado histórico.",
        "Não ranquear A contra B pela magnitude; adoção está condicionada a uma única validação e à falha D descoberta.",
    )
    add(
        "paper-eda_monthly_market",
        "eda_monthly_market",
        "`figures/eda_monthly_market.{png,svg}`",
        "Contexto dos dados",
        "Mostrar histórico da oferta/demanda atendida e janelas do estudo.",
        "X: meses 2000–2025; Y: passageiros pagos/assentos mensais; duas linhas, faixas validação/teste e lacunas.",
        "`analysis.py::eda`, analytics/fact_route_month e calendário; figura já existente, não regenerada nesta auditoria.",
        "É descrição observada do mercado, não série de previsão.",
        "Sustenta descrição histórica e a ausência global de quatro meses.",
        "Inclui totais do período de teste já expostos; não prova teste cego. Não foi relida a série 2024–2025 para esta auditoria.",
    )
    add(
        "paper-eda_concentration",
        "eda_concentration",
        "`figures/eda_concentration.{png,svg}`",
        "Contexto dos dados",
        "Explicar a concentração do universo antes da validação.",
        "X: Top N, escala log; Y: participação acumulada em 2022. Aeroportos por movimentos e rotas por passageiros.",
        "`analysis.py::eda`, fact_airport_month e fact_route_month, somente ranking 2022 na figura.",
        "Curvas têm unidades/universos diferentes apesar de compartilharem participação percentual.",
        "Justifica examinar grandes unidades; não demonstra cobertura universal ou escolha ótima do top 50.",
        "A escolhe top 50 por cutoff, não usa esta curva de 2022 como lista fixa para todos os anos.",
    )
    for module in ["a", "b", "d"]:
        for method in ["baseline", "lightgbm"]:
            add(
                "registry-" + module + "-" + method,
                "Model registry: " + module.upper() + " / " + method,
                "`web/components/dashboard/data-views.tsx::ModelPanel/MetricList`",
                module.upper(),
                "Identificar o método e a seleção histórica, sem confundir disponibilidade com serving preditivo.",
                "Sem eixos; lista de métricas principais, unidade e período; badge Selected method quando selecionado.",
                "GET /v2/models, exportado de reports/models por _validation_cards; D contém pax e seats.",
                "Valores são de validação 2023; seleção usa critério agregado (ambos os targets para D).",
                "Permite rastrear baseline e LightGBM lado a lado, com A mantendo a regra.",
                "Pode faltar se o payload não foi exportado/API falhar; o showcase estático é independente. Não é nova curva ou prova de forecast operacional.",
            )
    add(
        "registry-c",
        "Model registry: C not trained",
        "`web/components/dashboard/data-views.tsx::MlStudioView`",
        "C",
        "Expor ausência de treinamento sem fabricar score.",
        "Sem eixos ou métricas; status textual.",
        "GET /v2/models, card module-c criado em serving/export.py.",
        "O gate de qualidade de bagagem não é treinamento de modelo.",
        "Não há previsão C validada.",
        "Não interpretar o status como inferência de bagagem individual ou recomendação de cobrança.",
    )
    web_charts = [
        e
        for e in entries
        if e["id"].startswith("web-")
        and "-kpi-" not in e["id"]
        and not e["id"].endswith("horizon-table")
    ]
    figures = [e for e in entries if e["id"].startswith("paper-")]
    assert len(web_charts) == 26 and len(figures) == 37
    actual = {p.stem for p in (ROOT / "research/ml-showcase/figures").glob("*.png")}
    expected = {e["id"].removeprefix("paper-") for e in figures}
    assert actual == expected, (actual - expected, expected - actual)
    text = """# Catálogo de visualizações

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

"""
    for e in entries:
        text += f"""## {e["id"]} — {e["name"]}

1. **Localização:** {e["location"]}.
2. **Modelo/experimento:** {e["task"]}.
3. **Objetivo:** {e["purpose"]}
4. **Eixos, unidade e legenda:** {e["axes"]}
5. **Dados e proveniência:** {e["data"]}
6. **Leitura estatística:** {e["interpretation"]}
7. **Conclusão sustentada:** {e["conclusion"]}
8. **Limites e leituras incorretas:** {e["limits"]}

"""
    write("VISUALIZATION_CATALOG.md", text)
    (OUT / "visualization-inventory.json").write_text(
        json.dumps(
            {
                "web_charts": 26,
                "web_tables": 4,
                "web_kpis": 16,
                "registry_panels": 7,
                "report_figures": 37,
                "items": entries,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def architecture(v: dict) -> None:
    text = """# Arquitetura de Machine Learning

Escopo desta branch: ML e sua apresentação, sobre o commit base `22a120a`.
Nenhuma alteração no Analyst, infraestrutura da v3, API publicada ou Power BI.

```mermaid
flowchart TD
    A[Snapshot CSV ANAC] --> B[Ingestão e DQ: flights]
    B --> C[Painéis: aeroporto-dia e rota-companhia-mês]
    C --> D[Features por origem e cutoff]
    C --> E[Targets separados até 2023]
    D --> F[Splits cronológicos e purge]
    E --> F
    F --> G[Baselines determinísticos]
    F --> H[Seleção LightGBM: fitting e stopping 2022]
    G --> I[Comparação de validação 2023]
    H --> J[Predições de seleção persistidas]
    J --> I
    I --> K[Relatórios e análise de erros]
    H --> L[Refit final com rounds fixados]
    L --> M[Boosters congelados models/v1]
    K --> N[Payload estático showcase.json]
    K --> O[Payloads serving e registro da API]
    N --> P[Next.js ML Studio]
    O --> P
    M -. sem endpoint de inferência .-> Q[Serving preditivo ainda ausente]
```

## Contratos e responsabilidades

| Camada | Arquivos / evidência | Responsabilidade e risco |
|---|---|---|
| Ingestão | `src/anac/ingestion`, `data/processed/flights` | DQ, referência de datas e flags; não reconstruída nesta auditoria |
| Painéis | `features/panels.py`, `data/features/v1/panels` | Contagens por endpoint e escopo passageiro; painéis contêm datas além da validação, mas a auditoria não abriu seus targets de teste |
| Features | `daily.py`, `monthly.py`, `contracts.py` | Histórico limitado ao cutoff; calendário futuro permitido; schema/stamp/chave validados |
| Divisão | `splits.py`, `configs/features.toml` | Exclusão de meses desconhecidos no caminho supervisionado e guards de teste; purge por distância |
| Baselines | `evaluation/baselines.py` | Regras de comparação com fallback explícito; nada de target como entrada |
| Treino | `models/train.py`, `configs/models.toml` | Escalas/pesos, seleção, refit separado, FrozenModelExists |
| Avaliação | `evaluation/metrics.py`, `reports/models` | Fórmulas e bootstrap; reports v1 imutáveis nesta revisão |
| Auditoria | `scripts/audit_ml.py`, `results/audit.json` | Fonte parametrizada e somente leitura, hashes antes/depois, oráculo NumPy e replay de compare |
| Apresentação | `analysis.py`, `web/public/ml/showcase.json` | Agregações e amostra limitada de pares; não chamar de “sem dados de linha” |
| Relatório | `REPORT.md/html/pdf`, `web/public/ml/report.pdf` | Documento histórico com erratas e PDF regenerado, preservando as figuras anteriores |
| Interface | `ml-showcase.tsx`, `ml-charts.tsx` | Leitura/seleção de resultados, explicações e tooltips; nenhum treino/inferência |

## Dados e artefatos

Arquivos de modelo/predições/datasets são ignorados pelo Git; a auditoria aponta para uma
raiz de artefatos existente, sem copiar `.env` nem reutilizar instalação editável de outro worktree.
São carregados somente features/targets supervisionados já limitados a 2023 e predições salvas.
Os `.txt` finais são autenticados por hash; não usados para obter novos scores de validação.
O hash dos painéis é uma leitura binária de integridade, não avaliação de targets 2024–2025.

A rastreabilidade v1 tem limites: digest de dataset por nomes/tamanhos, vocabulários sem hash
no manifest e commit de treino com árvore suja. Um protocolo futuro deve registrar conteúdo,
versões, código/config completos, vocabulário, ranges efetivos e identidade do modelo selecionado.

## Endpoints reais

| Caminho | Origem e propósito | O que não faz |
|---|---|---|
| `GET /v2/models` | `serving/export.py::build_models/_validation_cards`, relatórios estáticos A/B/D + baselines | Não carrega booster nem executa predict |
| `GET /v2/modules` | Descrição dos módulos/contratos | Não demonstra que C foi treinado |
| `GET /v2/datasets` | Metadados de datasets e lacunas | Não comprova vintage histórico |
| `GET /ml/showcase.json` | Arquivo estático Next.js | Não é endpoint FastAPI nem previsão atual |
| `GET /ml/report.pdf` | PDF histórico versionado | Não é relatório recalculado a cada acesso |
| Analyst/tool models | Consulta o mesmo catálogo de resultados | Texto generativo não é previsão LightGBM; nenhuma chamada LLM foi executada nesta auditoria |

A API valida envelopes via Pydantic; ausência de payload resulta em 503, não dados inventados.
Nenhuma rota `/predict` consta do conjunto v2 auditado. Scripts `06_api.py` e outros legados
não são o serviço ativo. Não se criou endpoint novo nem mudou contrato compartilhado com Claude.

## Correções sem contaminar a versão congelada

O loader/baseline corrigidos rejeitam meses globalmente ausentes antes de zerar uma rota inativa.
Targets e features selados são rejeitados por índice mensal ou data diária. AP agrupa empates.
O KPI B passa a mostrar viés ponderado em pp, preservando o campo relativo antigo para
rastreabilidade. O payload/generator guardam o novo campo explicitamente.
Qualquer treino real corrigido requer saída nova (`models/v2` ou outro nome), nunca overwrite v1.
Não houve migração automática, rebuild dos Parquets, deploy ou promoção do modelo corrigido.
Em clones novos, o typecheck do Next.js agora executa `next typegen` antes de `tsc`,
pois `LayoutProps` depende dos tipos gerados de rotas nesta versão.

## Reprodução da auditoria

```powershell
py -3.12 -m venv .venv
.venv\\Scripts\\python -m pip install -r requirements-lock.txt
.venv\\Scripts\\python -m pip install -e . --no-deps
.venv\\Scripts\\python scripts/audit_ml.py --artifact-root D:\\anac-flight-intelligence-api-main
.venv\\Scripts\\python scripts/build_ml_audit_docs.py
.venv\\Scripts\\python -m pytest
```

`--artifact-root` pode ser outra pasta que contenha os artefatos históricos esperados;
não aponta implicitamente para o worktree principal. O script verifica hashes antes/depois.
A evidência não exige rebuild/ingestão nem novos modelos. `--refit` do estudo antigo não foi
executado e não deve ser usado para alegar identidade após a correção do loader D.
"""
    write("ML_ARCHITECTURE.md", text)


def prediction_guide(v: dict) -> None:
    payload = json.loads((ROOT / "web/public/ml/showcase.json").read_text(encoding="utf-8"))
    text = """# Guia das previsões: o que existe e o que falta

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
"""
    for key in ["a", "d_pax"]:
        e = payload["tasks"][key]["examples"]["best"]
        p = e["points"][0]
        text += f"| {TASKS[key][0]} | {e['entity']} | {p.get('date', p.get('month'))} | {p['actual']:.1f} | {p['model']:.1f} | {p['baseline']:.1f} |\n"
    text += """
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
"""
    write("PREDICTION_GUIDE.md", text)


def interview_guide(v: dict) -> None:
    text = """# Defesa técnica — iFood GenAI Internship / AI Builder

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
"""
    write("INTERVIEW_GUIDE.md", text)


def main() -> None:
    v = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    if v["status"] != "passed":
        raise ValueError("Only reconciled evidence may generate these docs")
    OUT.mkdir(parents=True, exist_ok=True)
    model_catalog(v)
    experiment_results(v)
    visualization_catalog(v)
    prediction_guide(v)
    architecture(v)
    interview_guide(v)
    print("Six audit documents and visualization inventory generated")


if __name__ == "__main__":
    main()
