# Relatório de ingestão e auditoria: ANAC Flight Intelligence 2.0

Execução completa de 2026-11-06. Figuras por ano geradas de [independent_audit.json](independent_audit.json) e [audit_drilldown.json](audit_drilldown.json). Nenhum modelo foi treinado.

## 1. Veredito

**Podemos seguir para a engenharia de atributos, com condições.** A ingestão é confiável: toda linha do CSV foi contabilizada e os totais batem com uma releitura independente. Os problemas restantes estão na própria base, e dois deles mudam o plano:

1. **Faltam 4 meses inteiros:** 2015-08, 2016-02, 2018-07, 2020-08. Em 2018, único caso que pude testar, a comparação com a ANAC indica que os voos existiram e só não estão neste CSV. Os outros três seguem o mesmo padrão, mas não foram testados.
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
| Linhas processadas | 22.120.241 em 308 arquivos mensais |
| Tempo total | 8.0 min (42.2 MB/s) |
| Pico de RAM do processo | 2.368 GB (limite: 12 GB) |
| Parquet final | 1.18 GB, compressão de 17.11x |
| Avisos e erros no log | 0 |
| Ambiente | Python 3.12.10, Polars 2.1.0, DuckDB 2.0.0 |

O CSV original está intacto: SHA-256 `69709a17376b74cea029a5730f07f2b9130aa31798b9d5b8a61d204cb81a91ab`, idêntico antes e depois do processamento.

## 3. Auditoria independente

O script de auditoria não compartilha código com o pipeline. Ele usa DuckDB e relê o CSV bruto com outro parser.

| Verificação | Resultado |
|---|---|
| Linhas físicas do CSV (contagem de quebras de linha) | 22.120.241: igual às publicadas |
| Rodapés dos Parquets | 22.120.241: igual |
| CSV bruto x Parquet, por ano | Diferença **zero** em linhas, passageiros, decolagens, assentos, km e horas nos 26 anos |
| Esquema | 1 única variante em 308 arquivos |
| Arquivos temporários restantes | 0 |
| Partição errada, ou ano/mês divergente da data | 0 |
| `id_basica` repetido | 0 em toda a base |
| Duplicatas recontadas do zero | 26.040: igual à flag |
| Flags recontadas do zero | Iguais às do pipeline nas 7 regras verificadas |
| Distância por rota | 43 linhas a mais de 5% da mediana da rota, em 22.053.279 |

Os meses presentes não têm dias faltando (todos com 28 dias ou mais). A única variação brusca entre meses é a de 2020, com a queda de 88% em abril (pandemia).

## 4. Estatísticas por ano

Passageiros em milhões, sem as duplicatas sinalizadas. ⚠ = ano com mês faltando, portanto subestimado.

| Ano | Meses | Linhas | Pax pagos | Doméstico | Internac. | RPK/ASK | Cias | Duplicatas | Com flag | Excesso nulo |
|---|---|---|---|---|---|---|---|---|---|---|
| 2000 | 12 | 785.716 | 44,3 | 35,0 | 9,3 | 65,5% | 57 | 9.431 | 2,85% | 5,9% |
| 2001 | 12 | 820.949 | 46,3 | 38,1 | 8,2 | 62,1% | 61 | 14.347 | 2,83% | 5,1% |
| 2002 | 12 | 760.395 | 45,9 | 38,5 | 7,5 | 62,5% | 58 | 1.469 | 3,65% | 5,4% |
| 2003 | 12 | 620.556 | 43,0 | 34,6 | 8,3 | 67,9% | 54 | 26 | 1,60% | 7,2% |
| 2004 | 12 | 612.839 | 46,7 | 37,4 | 9,2 | 71,1% | 59 | 235 | 1,67% | 8,1% |
| 2005 | 12 | 652.744 | 55,6 | 44,8 | 10,8 | 73,8% | 67 | 8 | 2,17% | 8,2% |
| 2006 | 12 | 681.383 | 60,6 | 49,6 | 11,0 | 75,1% | 73 | 19 | 2,49% | 8,5% |
| 2007 | 12 | 745.311 | 66,1 | 53,7 | 12,4 | 72,6% | 71 | 67 | 2,78% | 8,6% |
| 2008 | 12 | 766.478 | 69,5 | 56,1 | 13,4 | 71,5% | 70 | 356 | 2,14% | 8,1% |
| 2009 | 12 | 838.704 | 76,5 | 63,7 | 12,8 | 70,3% | 80 | 35 | 2,79% | 7,4% |
| 2010 | 12 | 969.306 | 91,9 | 76,2 | 15,7 | 73,7% | 84 | 1 | 0,98% | 8,0% |
| 2011 | 12 | 1.100.433 | 107,2 | 89,0 | 18,2 | 75,1% | 76 | 1 | 0,79% | 8,5% |
| 2012 | 12 | 1.141.313 | 114,2 | 94,9 | 19,3 | 76,3% | 94 | 0 | 0,70% | 8,9% |
| 2013 | 12 | 1.099.606 | 115,2 | 94,9 | 20,2 | 77,7% | 96 | 0 | 0,74% | 9,4% |
| 2014 | 12 | 1.098.931 | 122,5 | 100,7 | 21,8 | 79,6% | 104 | 1 | 1,18% | 9,7% |
| 2015 ⚠ | 11 | 999.184 | 112,1 | 92,0 | 20,1 | 78,8% | 95 | 9 | 0,97% | 9,0% |
| 2016 ⚠ | 11 | 889.258 | 102,7 | 83,2 | 19,6 | 80,8% | 109 | 12 | 0,92% | 8,9% |
| 2017 | 12 | 947.583 | 114,3 | 92,1 | 22,3 | 83,1% | 100 | 14 | 1,08% | 8,8% |
| 2018 ⚠ | 11 | 887.172 | 108,2 | 85,9 | 22,3 | 81,4% | 100 | 6 | 1,20% | 9,6% |
| 2019 | 12 | 956.592 | 120,7 | 96,1 | 24,6 | 83,6% | 103 | 3 | 0,72% | 9,3% |
| 2020 ⚠ | 11 | 447.151 | 49,5 | 42,7 | 6,8 | 73,5% | 110 | 0 | 0,55% | 0,0% |
| 2021 | 12 | 605.877 | 67,8 | 62,9 | 4,9 | 71,6% | 106 | 0 | 0,67% | 0,0% |
| 2022 | 12 | 841.389 | 98,6 | 82,6 | 16,0 | 81,6% | 110 | 0 | 0,65% | 0,0% |
| 2023 | 12 | 929.081 | 113,8 | 91,9 | 21,9 | 83,5% | 112 | 0 | 0,66% | 0,0% |
| 2024 | 12 | 945.070 | 120,1 | 94,0 | 26,1 | 84,0% | 104 | 0 | 0,70% | 0,0% |
| 2025 | 12 | 977.220 | 131,8 | 101,9 | 29,9 | 84,8% | 106 | 0 | 0,67% | 0,0% |

## 5. Dados inválidos

| Categoria | Linhas | % da base |
|---|---|---|
| Rejeitadas (sem como identificar ou localizar) | 0 | 0% |
| Com valor ilegível, mantidas | 18 | 0,00008% |
| Com ao menos uma flag de qualidade | 309.544 | 1,40% |
| Bagagem nula (combustível: 6,42%) | 1.431.578 | 6,47% |
| Bagagem e combustível iguais a zero, mas não informados (estrangeiras, 2020+) | 385.877 | 1,74% |

Zero rejeição **não significa base limpa**. Rejeitamos só o que não tem como ser identificado; o resto é sinalizado. E os dois últimos itens mostram o principal: nenhuma regra por linha detecta um zero que na verdade significa "não informado".

| Flag | Linhas | % |
|---|---|---|
| Passageiros (pagos + grátis) acima dos assentos | 117.627 | 0,532% |
| Natureza internacional em trecho entre aeroportos do Brasil | 74.637 | 0,337% |
| Distância igual a zero | 66.119 | 0,299% |
| Origem igual ao destino | 47.675 | 0,216% |
| Mesmo voo repetido com outro `id_basica` | 26.040 | 0,118% |
| Sem data ou hora de partida | 21.473 | 0,097% |
| Sem decolagem (`DUPLICATED LEG`) | 19.293 | 0,087% |
| Horas voadas diferem de chegada menos partida | 19.258 | 0,087% |
| RPK difere de passageiros x km | 16.240 | 0,073% |
| Passageiros sem assentos | 11.673 | 0,053% |
| ASK difere de assentos x km | 10.241 | 0,046% |
| Partida a mais de 3 dias da data de referência | 4.152 | 0,019% |
| Código ICAO fora do padrão | 942 | 0,004% |
| Métrica negativa | 121 | 0,001% |
| Valor ilegível (`24:00:00` na chegada) | 18 | 0,000% |
| Mais de 30 horas de voo | 14 | 0,000% |
| Chegada antes da partida | 0 | 0,000% |
| Ano ou mês divergente da data de referência | 0 | 0,000% |

Outros valores extremos, todos mantidos: 1 partida datada de 2032; 416 linhas com mais de um ano entre partida e referência; voo com 8.748 horas; 60.260 linhas com ocupação paga acima de 100% (12.716 acima de 150%); combustível de até −16.672 litros.

## 6. Principais problemas

### Meses ausentes (crítico para séries temporais)

Não há nenhuma linha com referência em 2015-08, 2016-02, 2018-07, 2020-08, nem no CSV bruto, nem arquivo-fonte com esse sufixo. Não é perda do pipeline.

Para julho de 2018, a comparação externa indica que os voos existiram. Os totais de 2019 e 2025 ficam a cerca de 1–2% dos da ANAC, mas o de 2018 fica 8% abaixo, próximo do peso de um mês:

| Ano | Base | ANAC | Diferença |
|---|---|---|---|
| 2025, total | 131,8 mi | 129,6 mi | 1,7% |
| 2025, doméstico | 101,9 mi | 101,2 mi | 0,6% |
| 2025, internacional | 29,9 mi | 28,4 mi | 5,4% |
| 2019, total | 120,7 mi | 119,4 mi | 1,1% |
| 2019, decolagens internacionais | 146.422 | cerca de 146 mil | praticamente igual |
| **2018, total (julho ausente)** | **108,2 mi** | **cerca de 117,8 mi (calculado)** | **-8,1%** |

O total de 2018 é calculado a partir do crescimento de 1,4% informado para 2019. A base soma passageiros pagos de todas as linhas, e a imprensa pode usar outro escopo, o que pode explicar parte das diferenças. Atualização: nos controles posteriores, RPK coincide com o agregado oficial, e só os passageiros divergem. A hipótese é que o CSV some por etapa. Veja [a proposta da etapa 2](../../docs/etapa2_proposta.md).

**Risco se ignorado:** defasagens calculadas por posição pulam um mês sem aviso, e os totais de 2015, 2016, 2018 e 2020 parecem quedas reais de demanda.

### Bagagem: zero não significa "sem excesso" (crítico para o Modelo C)

- **Estrangeiras nunca reportaram.** Cerca de 97–100% de nulos em bagagem e combustível até 2019, e 100% de **zeros** a partir de 2020. O nulo virou zero na fonte, por isso `has_excess_baggage = false` é falso nesses casos. O mesmo vale para `lt_combustivel = 0`.
- **Entre as brasileiras, as mudanças são de reporte, não de comportamento.** A TAM vai de 0% a 54,5% em um ano, e volta a 0% em 2019. Percentual de voos com excesso maior que zero:

| Cia | 2012 | 2013 | 2014 | 2016 | 2018 | 2019 | 2021 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|---|
| AZU | 77,6% | 98,3% | 86,4% | 82,8% | 77,6% | 77,9% | 87,5% | 86,7% | 72,6% |
| GLO | 53,2% | 10,0% | 53,4% | 67,8% | 49,4% | 24,4% | 19,5% | 36,7% | 31,4% |
| TAM | 0,0% | 0,0% | 54,5% | 77,5% | 28,6% | 0,0% | 0,0% | 0,0% | 0,0% |

- **Em 2024, 31 de 34 companhias com ao menos mil voos têm 0% de excesso.** Só AZU, GLO e ACN aparecem com valores positivos entre as maiores.
- **Mudança de regra.** A bagagem despachada grátis por passageiro cai a partir de 2017 (GLO: 11,4 kg em 2016, 6,2 kg em 2019), período em que a cobrança por mala passou a valer. Há coincidência temporal, mas este dado não prova causa.

### Outros pontos

- **Duplicatas:** 26.040 linhas, 97% em 2000–2002 (máximo de 1,75%, em 2001). **Corrijo o que escrevi antes:** a estimativa de 3,5–12% para 2001 era efeito da amostragem por blocos.
- **Code-share não indica contagem dupla.** São 1.551.640 linhas (7%, quase todas da TAM), com decolagem igual a 1. Por ano, de 0,4% a 2,8% têm voo de outra companhia no mesmo minuto e rota, faixa parecida com a dos voos regulares (0,3% a 2,2%). O teste exige horário exato, portanto é forte evidência, não prova.
- **`cd_di = C` some em 2018,** e `ds_natureza_tipo_linha` está "não identificada" em 5–12% das linhas. São categorias instáveis no tempo, um risco como variável de modelo.
- **Relógio.** Partida e chegada usam o mesmo relógio, e a hora mais calma do tráfego doméstico fica entre 1h e 4h em todos os 26 anos, sem mudança de regime. Isso condiz com hora do Brasil e não com UTC, mas **não encontrei o dicionário oficial da ANAC para confirmar**.
- **Companhias:** a PTB tem 31 meses faltando em seu período ativo, e 20 códigos ICAO têm mais de um nome. A ausência de uma companhia nem sempre significa ausência de voos.
- **Consumo dos Parquets:** o DuckDB lê `month=08` como texto. Use `dt_referencia` ou converta `month` para inteiro.

## 7. Confiabilidade por módulo

**A. Volume por aeroporto.** Decolagens e rotas são os campos mais sólidos. Use `dt_referencia` e `nr_decolagem`, sem duplicatas. Escopo operacional: 22.074.908 linhas. O período de pandemia precisa de tratamento explícito na validação. Não dá para falar em congestionamento: a base mede voos operados, e não filas ou atrasos.

**B. Ocupação.** Escopo disponível: 20.938.830 linhas. O alvo é pago sobre assentos operados, então ele exclui passageiros grátis. Os assentos também são os do voo realizado, não os publicados na malha: usá-los como entrada presume conhecer o avião de antemão, e isso precisa ser decidido e documentado.

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
.venv\Scripts\anac-ingest full --confirm-full
.venv\Scripts\python scripts\audit_processed.py
.venv\Scripts\python scripts\audit_drilldown.py
.venv\Scripts\python scripts\build_ingestion_report.py
```

## Fontes

- [Agência iNFRA, 20/01/2026](https://agenciainfra.com/blog/aviacao-brasileira-bate-recorde-e-chega-a-1296-mi-de-passageiros/): números de 2025.
- [Passageiro de Primeira, 27/08/2020](https://passageirodeprimeira.com/?p=150398): números de 2019, atribuídos ao Anuário do Transporte Aéreo.
- [Monitor Mercantil](https://monitormercantil.com.br/anac-abre-microdados-das-tarifas-aereas-de-maio/): microdados de tarifas da ANAC.
- [Consumidor Moderno](https://consumidormoderno.com.br/oficial-cobranca-extra-bagagem-valendo/): início da cobrança por bagagem.
