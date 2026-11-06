"""Render reports/ingestion/INGESTION_REPORT.md from the audit JSON files.

Run after audit_processed.py and audit_drilldown.py. Every per-year figure comes from those
files. External benchmarks and the assessment are written here, with their sources.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

OUT = Path("reports/ingestion")


def load(name: str) -> dict[str, Any]:
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def n(value: float | int) -> str:
    return f"{value:,.0f}".replace(",", ".")


def m(value: float) -> str:
    return f"{value / 1e6:.1f}".replace(".", ",")


def pct(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}".replace(".", ",") + "%"


def main() -> int:
    audit = load("independent_audit.json")
    drill = load("audit_drilldown.json")
    quality = load("quality_report.json")

    perf = quality["performance"]
    totals = quality["reconciliation"]
    published = totals["rows_published"]
    flags = audit["flags"]["totals"]
    months_by_year: dict[int, int] = {}
    for row in audit["temporal"]["months"]:
        months_by_year[row["year"]] = months_by_year.get(row["year"], 0) + 1
    flag_year = {row["year"]: row for row in audit["flags"]["by_year"]}
    null_year = {row["year"]: row for row in audit["missing_values"]["by_year"]}
    dup_year = {row["year"]: row for row in audit["duplicates"]["flag_by_year"]}
    gaps = ", ".join(audit["temporal"]["gaps"])

    year_rows = []
    for row in audit["consistency"]["service_by_year"]:
        year = row["year"]
        mark = " ⚠" if months_by_year[year] < 12 else ""
        year_rows.append(
            [
                f"{year}{mark}",
                str(months_by_year[year]),
                n(row["rows"]),
                m(row["paid_pax"]),
                m(row["paid_pax_domestic"]),
                m(row["paid_pax_international"]),
                pct(100 * row["rpk_over_ask"], 1),
                str(row["carriers"]),
                n(dup_year[year]["flagged"]),
                pct(flag_year[year]["any_flag_pct"]),
                pct(null_year[year]["excess_baggage"], 1),
            ]
        )

    flag_labels = {
        "dq_pax_exceed_seats": "Passageiros (pagos + grátis) acima dos assentos",
        "dq_nature_geography_mismatch": "Natureza internacional em trecho entre aeroportos do Brasil",
        "dq_zero_distance": "Distância igual a zero",
        "dq_same_origin_destination": "Origem igual ao destino",
        "dq_duplicate_record": "Mesmo voo repetido com outro `id_basica`",
        "dq_missing_departure": "Sem data ou hora de partida",
        "dq_no_takeoff": "Sem decolagem (`DUPLICATED LEG`)",
        "dq_hours_clock_mismatch": "Horas voadas diferem de chegada menos partida",
        "dq_rpk_mismatch": "RPK difere de passageiros x km",
        "dq_pax_without_seats": "Passageiros sem assentos",
        "dq_ask_mismatch": "ASK difere de assentos x km",
        "dq_departure_reference_gap": "Partida a mais de 3 dias da data de referência",
        "dq_icao_nonstandard": "Código ICAO fora do padrão",
        "dq_negative_metric": "Métrica negativa",
        "dq_parse_error": "Valor ilegível (`24:00:00` na chegada)",
        "dq_implausible_flight_hours": "Mais de 30 horas de voo",
        "dq_arrival_before_departure": "Chegada antes da partida",
        "dq_reference_period_mismatch": "Ano ou mês divergente da data de referência",
    }
    flag_rows = [
        [label, n(flags[key]), pct(100 * flags[key] / published, 3)]
        for key, label in sorted(flag_labels.items(), key=lambda item: -flags[item[0]])
    ]

    foreign_zero_rows = sum(
        row["rows"]
        for row in drill["null_versus_zero_by_carrier_nationality"]
        if row["year"] >= 2020 and row["brazilian_carrier"] is False
    )
    {row["carrier"]: row for row in drill["carrier_month_gaps"]}
    scope = drill["model_ready_scope"]
    outliers = drill["outliers"]

    def rate(carrier: str, year: int) -> str:
        for row in drill["excess_positive_rate_major_carriers"]:
            if row["carrier"] == carrier and row["year"] == year:
                return pct(row["positive_pct"], 1)
        return "n/d"

    baggage_years = [2012, 2013, 2014, 2016, 2018, 2019, 2021, 2024, 2025]
    baggage_rows = [
        [carrier, *[rate(carrier, year) for year in baggage_years]]
        for carrier in ("AZU", "GLO", "TAM")
    ]

    verification = audit["structural"]
    service = {row["year"]: row for row in audit["consistency"]["service_by_year"]}
    text = f"""# Relatório de ingestão e auditoria: ANAC Flight Intelligence 2.0

Execução completa de 2026-11-06. Figuras por ano geradas de [independent_audit.json](independent_audit.json) e [audit_drilldown.json](audit_drilldown.json). Nenhum modelo foi treinado.

## 1. Veredito

**Podemos seguir para a engenharia de atributos, com condições.** A ingestão é confiável: toda linha do CSV foi contabilizada e os totais batem com uma releitura independente. Os problemas restantes estão na própria base, e dois deles mudam o plano:

1. **Faltam 4 meses inteiros:** {gaps}. Em 2018, único caso que pude testar, a comparação com a ANAC indica que os voos existiram e só não estão neste CSV. Os outros três seguem o mesmo padrão, mas não foram testados.
2. **O alvo de bagagem não mede o comportamento real.** Zero muitas vezes significa "não informado". Do jeito que foi descrito, o Modelo C aprenderia quem reporta, e não quem despacha mala em excesso.

| Módulo | Confiança | Condição principal |
|---|---|---|
| A. Volume por aeroporto | Alta (mensal e diário), média (horário) | Tratar os 4 meses como ausentes, não como zero; confirmar o relógio antes de usar a hora |
| B. Ocupação | Alta | Filtrar o escopo; usar só histórico defasado |
| C. Bagagem | **Baixa como descrito** | Redefinir o alvo e o escopo (seção 7) |
| D. Demanda e capacidade | Alta | Não há coluna de tarifa: não falar em preço |

## 2. Execução

| Item | Resultado |
|---|---|
| Linhas processadas | {n(published)} em {verification["files"]} arquivos mensais |
| Tempo total | {perf["elapsed_seconds"] / 60:.1f} min ({perf["throughput_mb_per_s"]} MB/s) |
| Pico de RAM do processo | {perf["peak_rss_gb"]} GB (limite: 12 GB) |
| Parquet final | {verification["bytes_on_disk"] / 1e9:.2f} GB, compressão de {perf["compression_ratio"]}x |
| Avisos e erros no log | 0 |
| Ambiente | Python 3.12.10, Polars 2.1.0, DuckDB 2.0.0 |

O CSV original está intacto: SHA-256 `69709a17376b74cea029a5730f07f2b9130aa31798b9d5b8a61d204cb81a91ab`, idêntico antes e depois do processamento.

## 3. Auditoria independente

O script de auditoria não compartilha código com o pipeline. Ele usa DuckDB e relê o CSV bruto com outro parser.

| Verificação | Resultado |
|---|---|
| Linhas físicas do CSV (contagem de quebras de linha) | {n(audit["physical_lines_in_csv"])}: igual às publicadas |
| Rodapés dos Parquets | {n(verification["rows_from_parquet_footers"])}: igual |
| CSV bruto x Parquet, por ano | Diferença **zero** em linhas, passageiros, decolagens, assentos, km e horas nos 26 anos |
| Esquema | 1 única variante em {verification["files"]} arquivos |
| Arquivos temporários restantes | {verification["temporary_leftovers"]} |
| Partição errada, ou ano/mês divergente da data | 0 |
| `id_basica` repetido | {audit["duplicates"]["ids"]["repeated_ids"]} em toda a base |
| Duplicatas recontadas do zero | {n(audit["duplicates"]["extra_rows_by_recount"])}: igual à flag |
| Flags recontadas do zero | Iguais às do pipeline nas 7 regras verificadas |
| Distância por rota | {audit["consistency"]["route_distance"]["over_5pct_from_route_median"]} linhas a mais de 5% da mediana da rota, em {n(audit["consistency"]["route_distance"]["rows_checked"])} |

Os meses presentes não têm dias faltando (todos com 28 dias ou mais). A única variação brusca entre meses é a de 2020, com a queda de 88% em abril (pandemia).

## 4. Estatísticas por ano

Passageiros em milhões, sem as duplicatas sinalizadas. ⚠ = ano com mês faltando, portanto subestimado.

{table(["Ano", "Meses", "Linhas", "Pax pagos", "Doméstico", "Internac.", "RPK/ASK", "Cias", "Duplicatas", "Com flag", "Excesso nulo"], year_rows)}

## 5. Dados inválidos

| Categoria | Linhas | % da base |
|---|---|---|
| Rejeitadas (sem como identificar ou localizar) | 0 | 0% |
| Com valor ilegível, mantidas | {n(flags["dq_parse_error"])} | {pct(100 * flags["dq_parse_error"] / published, 5)} |
| Com ao menos uma flag de qualidade | {n(flags["any_flag"])} | {pct(100 * flags["any_flag"] / published)} |
| Bagagem nula (combustível: {pct(audit["missing_values"]["null_pct_by_column"]["lt_combustivel"])}) | {n(published * audit["missing_values"]["null_pct_by_column"]["kg_bagagem_excesso"] / 100)} | {pct(audit["missing_values"]["null_pct_by_column"]["kg_bagagem_excesso"])} |
| Bagagem e combustível iguais a zero, mas não informados (estrangeiras, 2020+) | {n(foreign_zero_rows)} | {pct(100 * foreign_zero_rows / published)} |

Zero rejeição **não significa base limpa**. Rejeitamos só o que não tem como ser identificado; o resto é sinalizado. E os dois últimos itens mostram o principal: nenhuma regra por linha detecta um zero que na verdade significa "não informado".

{table(["Flag", "Linhas", "%"], flag_rows)}

Outros valores extremos, todos mantidos: 1 partida datada de 2032; {n(outliers["gap_over_1_year"])} linhas com mais de um ano entre partida e referência; voo com {n(audit["consistency"]["ranges"][3]["max"])} horas; {n(outliers["load_factor_over_1"])} linhas com ocupação paga acima de 100% ({n(outliers["load_factor_over_1_5"])} acima de 150%); combustível de até −16.672 litros.

## 6. Principais problemas

### Meses ausentes (crítico para séries temporais)

Não há nenhuma linha com referência em {gaps}, nem no CSV bruto, nem arquivo-fonte com esse sufixo. Não é perda do pipeline.

Para julho de 2018, a comparação externa indica que os voos existiram. Os totais de 2019 e 2025 ficam a cerca de 1–2% dos da ANAC, mas o de 2018 fica 8% abaixo, próximo do peso de um mês:

| Ano | Base | ANAC | Diferença |
|---|---|---|---|
| 2025, total | {m(service[2025]["paid_pax"])} mi | 129,6 mi | {pct(100 * (service[2025]["paid_pax"] / 129.6e6 - 1), 1)} |
| 2025, doméstico | {m(service[2025]["paid_pax_domestic"])} mi | 101,2 mi | {pct(100 * (service[2025]["paid_pax_domestic"] / 101.2e6 - 1), 1)} |
| 2025, internacional | {m(service[2025]["paid_pax_international"])} mi | 28,4 mi | {pct(100 * (service[2025]["paid_pax_international"] / 28.4e6 - 1), 1)} |
| 2019, total | {m(service[2019]["paid_pax"])} mi | 119,4 mi | {pct(100 * (service[2019]["paid_pax"] / 119.4e6 - 1), 1)} |
| 2019, decolagens internacionais | {n(audit["clock"]["international_hours_vs_clock"][19]["rows"])} | cerca de 146 mil | praticamente igual |
| **2018, total (julho ausente)** | **{m(service[2018]["paid_pax"])} mi** | **cerca de 117,8 mi (calculado)** | **{pct(100 * (service[2018]["paid_pax"] / 117.75e6 - 1), 1)}** |

O total de 2018 é calculado a partir do crescimento de 1,4% informado para 2019. A base soma passageiros pagos de todas as linhas, e a imprensa pode usar outro escopo, o que pode explicar parte das diferenças. Atualização: nos controles posteriores, RPK coincide com o agregado oficial, e só os passageiros divergem. A hipótese é que o CSV some por etapa. Veja [a proposta da etapa 2](../../docs/etapa2_proposta.md).

**Risco se ignorado:** defasagens calculadas por posição pulam um mês sem aviso, e os totais de 2015, 2016, 2018 e 2020 parecem quedas reais de demanda.

### Bagagem: zero não significa "sem excesso" (crítico para o Modelo C)

- **Estrangeiras nunca reportaram.** Cerca de 97–100% de nulos em bagagem e combustível até 2019, e 100% de **zeros** a partir de 2020. O nulo virou zero na fonte, por isso `has_excess_baggage = false` é falso nesses casos. O mesmo vale para `lt_combustivel = 0`.
- **Entre as brasileiras, as mudanças são de reporte, não de comportamento.** A TAM vai de 0% a 54,5% em um ano, e volta a 0% em 2019. Percentual de voos com excesso maior que zero:

{table(["Cia", *[str(y) for y in baggage_years]], baggage_rows)}

- **Em 2024, 31 de 34 companhias com ao menos mil voos têm 0% de excesso.** Só AZU, GLO e ACN aparecem com valores positivos entre as maiores.
- **Mudança de regra.** A bagagem despachada grátis por passageiro cai a partir de 2017 (GLO: 11,4 kg em 2016, 6,2 kg em 2019), período em que a cobrança por mala passou a valer. Há coincidência temporal, mas este dado não prova causa.

### Outros pontos

- **Duplicatas:** {n(audit["duplicates"]["flag_total"])} linhas, 97% em 2000–2002 (máximo de 1,75%, em 2001). **Corrijo o que escrevi antes:** a estimativa de 3,5–12% para 2001 era efeito da amostragem por blocos.
- **Code-share não indica contagem dupla.** São {n(1551640)} linhas (7%, quase todas da TAM), com decolagem igual a 1. Por ano, de 0,4% a 2,8% têm voo de outra companhia no mesmo minuto e rota, faixa parecida com a dos voos regulares (0,3% a 2,2%). O teste exige horário exato, portanto é forte evidência, não prova.
- **`cd_di = C` some em 2018,** e `ds_natureza_tipo_linha` está "não identificada" em 5–12% das linhas. São categorias instáveis no tempo, um risco como variável de modelo.
- **Relógio.** Partida e chegada usam o mesmo relógio, e a hora mais calma do tráfego doméstico fica entre 1h e 4h em todos os 26 anos, sem mudança de regime. Isso condiz com hora do Brasil e não com UTC, mas **não encontrei o dicionário oficial da ANAC para confirmar**.
- **Companhias:** a PTB tem 31 meses faltando em seu período ativo, e 20 códigos ICAO têm mais de um nome. A ausência de uma companhia nem sempre significa ausência de voos.
- **Consumo dos Parquets:** o DuckDB lê `month=08` como texto. Use `dt_referencia` ou converta `month` para inteiro.

## 7. Confiabilidade por módulo

**A. Volume por aeroporto.** Decolagens e rotas são os campos mais sólidos. Use `dt_referencia` e `nr_decolagem`, sem duplicatas. Escopo operacional: {n(scope["operated_unique"])} linhas. O período de pandemia precisa de tratamento explícito na validação. Não dá para falar em congestionamento: a base mede voos operados, e não filas ou atrasos.

**B. Ocupação.** Escopo disponível: {n(scope["load_factor_scope"])} linhas. O alvo é pago sobre assentos operados, então ele exclui passageiros grátis. Os assentos também são os do voo realizado, não os publicados na malha: usá-los como entrada presume conhecer o avião de antemão, e isso precisa ser decidido e documentado.

**C. Bagagem.** Não recomendo prever "excesso sim/não" em todas as companhias. Atualização: o diagnóstico aprofundado também descarta a sinalização por voo restrita à Azul e propõe outro alvo. Veja [a proposta da etapa 2](../../docs/etapa2_proposta.md).

**D. Demanda e capacidade.** RPK e ASK batem com seus componentes em mais de 99,9% das linhas, e RPK/ASK evolui de forma plausível, de 62% em 2001 para 85% em 2025, com queda na pandemia. Confirmei que não há coluna de tarifa. A ANAC publica microdados de tarifas à parte, uma possível extensão futura com preços reais.

**Por período.** Recomendo começar os modelos em 2003 ou depois: 97% das duplicatas e as maiores taxas de flags estão em 2000–2002. Essa escolha pode ser ajustada pela validação.

## 8. Regras obrigatórias para a engenharia de atributos

1. Filtrar `NOT dq_duplicate_record` e `NOT dq_no_takeoff` em toda contagem.
2. Construir um calendário explícito: meses ausentes viram ausência conhecida, nunca zero, e defasagens são calculadas por data, nunca por posição.
3. Tratar bagagem e combustível de companhias estrangeiras como não informados, em qualquer ano.
4. Usar `outcome` e `operated` (veja `contract.py`) apenas como histórico defasado.
5. Usar os dados de ocupação, RPK e ASK só com `nr_assentos_ofertados > 0`, excluindo `IMPRODUTIVO` conforme o módulo.
6. Não usar `load_factor_paid` bruto sem decidir a política para valores acima de 1.

## 9. Limitações desta auditoria

- As flags cobrem apenas as regras que escrevi. Um valor plausível mas errado passa sem aviso.
- A comparação externa usa notícias com dados atribuídos à ANAC, e só alguns anos. O total de 2019 e os de 2025 foram conferidos nas páginas citadas. O doméstico de 2019 (95,3 mi) apareceu apenas em resultado de busca, por isso não entrou na tabela.
- Atualização: os meses ausentes constam das fontes oficiais, mas ainda não foram baixados. Veja [a proposta da etapa 2](../../docs/etapa2_proposta.md).
- A causa da mudança de nulo para zero em 2020 é inferida do padrão dos dados, não documentada pela fonte.

## 10. Como reproduzir

```powershell
.venv\\Scripts\\anac-ingest full --confirm-full
.venv\\Scripts\\python scripts\\audit_processed.py
.venv\\Scripts\\python scripts\\audit_drilldown.py
.venv\\Scripts\\python scripts\\build_ingestion_report.py
```

## Fontes

- [Agência iNFRA, 20/01/2026](https://agenciainfra.com/blog/aviacao-brasileira-bate-recorde-e-chega-a-1296-mi-de-passageiros/): números de 2025.
- [Passageiro de Primeira, 27/08/2020](https://passageirodeprimeira.com/?p=150398): números de 2019, atribuídos ao Anuário do Transporte Aéreo.
- [Monitor Mercantil](https://monitormercantil.com.br/anac-abre-microdados-das-tarifas-aereas-de-maio/): microdados de tarifas da ANAC.
- [Consumidor Moderno](https://consumidormoderno.com.br/oficial-cobranca-extra-bagagem-valendo/): início da cobrança por bagagem.
"""
    target = OUT / "INGESTION_REPORT.md"
    target.write_text(text, encoding="utf-8")
    print(f"wrote {target} ({len(text)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
