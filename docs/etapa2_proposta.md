# Etapa 2: meses ausentes, bagagem e proposta de atributos

Situação em 2026-11-06. Nenhum modelo foi treinado, nenhum baseline foi calculado e nenhum arquivo externo foi integrado. Dados de apoio: [anac_portal_probe.json](../reports/ingestion/anac_portal_probe.json), [baggage_diagnostic.json](../reports/baggage/baggage_diagnostic.json) e [temporal_windows.json](../reports/features/temporal_windows.json).

## 1. Os quatro meses ausentes

**Conclusão: os quatro meses existem nas fontes oficiais e podem ser recuperados sem preenchimento artificial.** Falta só baixar os arquivos e validá-los.

### O que foi verificado

| Fonte | Conteúdo | Acesso por script | Situação dos 4 meses |
|---|---|---|---|
| [Microdados `basica`](https://www.gov.br/anac/pt-br/assuntos/regulados/empresas-aereas/envio-de-informacoes/microdados) | Mesmo nível do nosso CSV (voo), um ZIP por mês | **Não** (HTTP 403) | Listados na página, junto com `combinada`. **Tamanho e esquema não verificados** |
| [`Dados_Estatisticos.csv`](https://sistemas.anac.gov.br/dadosabertos/Voos%20e%20opera%C3%A7%C3%B5es%20a%C3%A9reas/Dados%20Estat%C3%ADsticos%20do%20Transporte%20A%C3%A9reo/) | Companhia x rota x mês, 361 MB, atualizado em 2026-11-06 | Sim | **Presentes** |
| [VRA](https://sistemas.anac.gov.br/dadosabertos/Voos%20e%20opera%C3%A7%C3%B5es%20a%C3%A9reas/Voo%20Regular%20Ativo%20%28VRA%29/) | Voos regulares com horário previsto e real, situação e justificativa | Sim | Pasta de 2018-07 presente (11,7 MB). Não traz passageiros |
| [RSA](https://sistemas.anac.gov.br/dadosabertos/Voos%20e%20opera%C3%A7%C3%B5es%20a%C3%A9reas/Registro%20de%20servi%C3%A7os%20a%C3%A9reos/) | Fotografias diárias da malha aprovada, com assentos, desde 2019 | Sim | Só 2020-08 está no período coberto |

A página de microdados lista todos os meses de 2015 a 2021 e vai até **2026-09**. Nosso CSV termina em 2025-12.

### Comparação com o agregado oficial

Testei Azul, Gol e TAM (a soma delas não é o mercado todo). O teste de controle usou os 8 meses vizinhos dos ausentes:

| Métrica | Parquet x agregado oficial nos meses vizinhos |
|---|---|
| Decolagens, assentos, RPK, ASK | **Diferença zero** nas 24 combinações de companhia e mês |
| Passageiros pagos | Nosso valor é **0,03% a 5,7% maior** |

Em decolagens e assentos, os meses ausentes têm o mesmo porte dos vizinhos:

| Mês ausente | Decolagens (AZU + GLO + TAM) | Passageiros pagos (AZU + GLO + TAM, valor oficial) |
|---|---|---|
| 2015-08 | 71.225 | 7,68 mi |
| 2016-02 | 64.163 | 6,87 mi |
| 2018-07 | 67.854 | 8,56 mi |
| 2020-08 | 19.668 | 2,20 mi |

### Dois achados novos

1. **A diferença em passageiros tem provável explicação.** Com RPK idêntico e menos passageiros, a hipótese é que o agregado conta quem segue na mesma aeronave uma só vez, enquanto o CSV soma por etapa (`basica`). Isso também explicaria os totais 1–2% acima da ANAC no relatório anterior. É uma hipótese, testável com um mês de `combinada`. Para ocupação, a soma por etapa continua correta, porque cada assento voa em uma etapa.
2. **A fonte é revisada.** Em 2025-12, nosso CSV tem 2,4% menos decolagens da Azul que o portal atual, enquanto Gol e TAM batem. Então, o CSV é uma foto antiga, e os últimos meses dele podem estar incompletos.

### Estratégia de integração proposta

Nada disso foi executado. Aguarda sua aprovação.

| Item | Proposta |
|---|---|
| Origem | `basica{AAAA}-{MM}.zip`, da página de microdados da ANAC |
| Arquivos | 4 meses ausentes + 2018-06 como controle + 2025-10 a 2025-12 para medir revisões |
| Tamanho | **Não verificado.** Estimo unidades a dezenas de MB por ZIP, pelo volume de linhas dos meses vizinhos |
| Como baixar | Você pelo navegador, em `data/raw/supplements/` (o portal bloqueia scripts, e não vou contornar isso) |
| CSV original | Intacto |
| Saída | Nova versão, `data/processed/flights_v2_1/`, sem alterar `flights/`, com coluna `_source` por linha |

Portões, em ordem. Se um falhar, paro e investigo:

1. **Esquema:** colunas, separador, codificação e formato decimal comparados com o contrato. Diferenças precisam de um mapeamento explícito.
2. **Definições:** no mês de controle, cada `id_basica` deve existir nos Parquets com os mesmos valores.
3. **Sobreposição:** nenhum `id_basica` dos meses novos pode já estar na base.
4. **Totais:** decolagens, assentos, RPK e ASK iguais aos do agregado oficial, por companhia.
5. **Auditoria:** repetir a auditoria independente na nova versão.

O agregado de 361 MB é útil como referência para todos os 308 meses. Se os ZIPs não puderem ser obtidos, ele sozinho já preenche os meses dos módulos mensais (B e D), mas não dá dados diários para o módulo A.

Foram baixados cerca de 47 MB em leituras parciais do agregado, 14 MB dos quais em uma primeira tentativa com ordenação errada, cujos números descartei. É mais do que eu havia estimado. Nada disso foi salvo além dos totais no JSON.

## 2. Diagnóstico do módulo de bagagem

**Conclusão: "excesso de bagagem" não é um alvo defensável no mercado como um todo. A bagagem total despachada por passageiro é.** Ainda não há decisão sobre o módulo.

### O que se observa

| Ano | Passageiros em companhias com excesso observável | Com bagagem livre observável | Companhias com excesso observável |
|---|---|---|---|
| 2003 | 85,6% | 88,2% | 11 |
| 2009 | 36,2% | 88,7% | 15 |
| 2015 | 87,0% | 88,0% | 6 |
| 2020 | 28,3% | 91,0% | 1 |
| 2025 | 50,5% | 84,4% | 4 |

"Observável" significa excesso acima de zero em ao menos 1% dos voos da companhia no mês. Entre 2000 e 2025, esse percentual oscila entre 28% e 90%, enquanto a bagagem livre fica estável em 84–94%.

### Consistência por companhia

| Companhia | Meses com excesso observável | Alternâncias | Observação |
|---|---|---|---|
| AZU | 201 de 201 | 0 | Único caso sem interrupção, mas com 11 saltos de 30 pontos ou mais |
| GLO | 263 de 296 | 5 | Excesso cai perto de zero depois de 2018 |
| TAM | 136 de 308 | 5 | **Nada desde 2018-05**, embora seja a maior em 2025 (44 mi de passageiros) |
| PTB | 90 de 271 | 23 | Liga e desliga |
| Estrangeiras | 0 | 0 | Nunca reportam |

### Três testes

1. **A sinalização por voo não é confiável nem na Azul.** Em 2025, a parcela de voos com excesso foi de 84,8% em abril para 7,1% em maio, 98,6% em junho e 22,5% em julho, enquanto os kg por passageiro quase não mudaram (0,253; 0,238; 0,228; 0,189). Isso indica como o valor foi registrado, e não o que os passageiros fizeram. **Descarta a classificação por voo, inclusive a restrita à Azul.**
2. **O peso não confirma a bagagem.** Nas brasileiras, `kg_peso = 75 × passageiros + bagagem + carga + correio` vale em 100% dos voos. Como é exato demais, `kg_peso` parece calculado, então essa igualdade não prova que a bagagem esteja correta.
3. **Estrangeiras têm um valor fixo.** Desde 2020, o peso delas implica exatamente **15,0 kg por passageiro**, embora a bagagem conste como zero. Parece um valor padrão aplicado na fonte. Consequência: `kg_peso` e RTK dessas companhias têm uma quebra em 2020.

### Persistência ano a ano por rota

Correlação de Spearman entre rota-mês e o mesmo mês do ano anterior, em voos domésticos, usando dados só até 2022:

| Alvo | AZU 2015–2022 | TAM 2015–2022 | GLO 2015–2018 | GLO 2019–2022 |
|---|---|---|---|---|
| kg de excesso por passageiro | 0,68 a 0,86 | Indefinida ou instável | 0,05 a 0,67 | −0,09 a 0,67 |
| kg **totais** por passageiro | 0,81 a 0,94 | 0,81 a 0,94 | 0,87 a 0,92 | **0,27 a 0,56** |

### Alvos avaliados

| Alvo | Veredito | Motivo |
|---|---|---|
| Excesso sim/não, todas as companhias | **Rejeitado** | Aprende quem reporta |
| Excesso sim/não, só Azul | **Rejeitado** | A sinalização por voo oscila sem relação com os kg |
| kg de excesso por passageiro, só Azul | Possível, não recomendado | Sólido, mas cobre uma só companhia (cerca de 25% dos passageiros) e tem valor limitado |
| **kg totais despachados por passageiro** (rota x companhia x mês, brasileiras) | **Recomendado** | Sempre observado; não depende de como cada companhia separa "livre" de "excesso"; persistente em duas das três grandes |
| Carga paga por rota x mês | **Alternativa** | Até 0,02% de nulos, cobre estrangeiras; mistura cargueiros (de 55% para 76% nas estrangeiras em 2020) |
| Atraso ou cancelamento (VRA) | Extensão futura | Alvo observável e útil, mas é outra base, ainda não auditada |

### Riscos do alvo recomendado

- **Quebra em 2017:** os kg por passageiro das brasileiras caem de 11,6 (2016) para 7,5 (2019), no período em que a cobrança por mala começou. Por isso o treino deveria começar em 2018.
- **Gol em 2019–2021:** a persistência cai, e 2020 tem só 3,99 kg por passageiro. Se isso for reporte, atinge o alvo. Precisa de investigação antes do treino.
- **Significado:** o campo se chama "livre", mas não encontrei o dicionário oficial. O alvo descreve kg declarados, não o comportamento de cada passageiro.

## 3. Princípios comuns

**Defasagem de publicação.** Em 2026-11-06, o último mês publicado era 2026-09. Por isso, assumo:

> Na origem `O` (início do mês), o último mês conhecido é `C = O − 2`. O alvo é `T = O + h`, então a distância até o último dado é `k = h + 2` meses.

Toda variável derivada dos dados deve vir de um mês `≤ C`. O valor `2` será um parâmetro, com sensibilidade testada para `3`.

**Quem entra na previsão.** A elegibilidade usa apenas dados `≤ C` (exemplo: rota ativa nos 3 meses até `C`). Usar os assentos do mês-alvo para filtrar seria vazamento por seleção. Limiares de porte são definidos só no treino.

**Meses ausentes.** Calendário explícito: meses ausentes são marcados como desconhecidos, nunca como zero, e defasagens são calculadas por data, nunca por posição.

## 4. Proposta por módulo

| | A. Volume por aeroporto | B. Ocupação | D. Demanda e capacidade |
|---|---|---|---|
| **Unidade** | Aeroporto x dia | Rota direcional x companhia x mês | Rota direcional x mês |
| **Alvo** | Pousos + decolagens no dia (`nr_decolagem`, por data real de partida e de chegada) | `Σ pagos / Σ assentos`, ponderado por assentos | `log1p` de passageiros pagos e de assentos, modelados separadamente; pressão = razão entre os dois |
| **Horizonte** | Todos os dias de `O+1` e `O+3` | `h` = 1, 3, 6 meses | `h` = 1, 3, 6 meses |
| **Escopo** | Top 50 aeroportos por histórico até `C` (90,9% dos movimentos em 2013–2022) | Passageiros, não `IMPRODUTIVO`, assentos > 0, sem duplicatas | Igual ao B, somando companhias |
| **Baseline obrigatório** | Mesmo dia da semana há 364 dias, ajustado pela tendência anual até `C` | Mesmo mês do ano anterior; média dos 12 meses até `C` | Mesmo mês do ano anterior ajustado pela tendência até `C` |
| **Modelo a comparar** | LightGBM | LightGBM; FT-Transformer só se LightGBM deixar erro explicável | LightGBM |
| **Métrica principal** | WAPE e MASE (sazonal de 364 dias) | MAE em pontos percentuais, ponderado por assentos | WAPE de passageiros e assentos; RMSSE |
| **Métricas secundárias** | Viés, cobertura do intervalo P10–P90, erro por porte | RMSE, viés, cobertura P10–P90, erro por porte e rota | PR-AUC e Brier do evento de alta pressão, calibração |

**Hora a hora fica de fora por enquanto.** O relógio não está confirmado, e aeroportos menores têm poucas horas ativas (em 2019: SBGR 99,6%, SBUL 42,9%, SBPJ 29,6%). O VRA pode ajudar a confirmar.

**Evento de alta pressão (D).** Ocupação acima de um limiar fixado só no treino. Como passageiros nunca passam muito dos assentos, a demanda observada é censurada: o módulo mede demanda *transportada*, não a demanda real, e não prevê tarifa nem causa.

**Sobrevivência (B).** Sem voos em `T`, a ocupação não existe. Reportarei o erro condicionado à operação e, separadamente, a taxa de operação.

### Atributos e disponibilidade

| Grupo | Atributos | A | B | D | Disponível porque |
|---|---|---|---|---|---|
| Calendário do alvo | Dia da semana, mês, feriados nacionais, Carnaval, dias úteis, férias escolares | ✓ | ✓ | ✓ | Conhecido de antemão |
| Identidade | Aeroporto, rota, companhia, região, UF, internacional, distância | ✓ | ✓ | ✓ | Estável; entidades novas viram "desconhecido" |
| Sazonal | Valor em `T−12` e `T−24`, perfil por dia da semana | ✓ | ✓ | ✓ | `k ≤ 12` garante `T−12 ≤ C` |
| Nível recente | Médias de 3, 6, 12 meses até `C` | ✓ | ✓ | ✓ | Só até `C` |
| Tendência | Variação de 12 meses medida em `C` | ✓ | ✓ | ✓ | Só até `C` |
| Rede | Ocupação da rota, da companhia e do aeroporto até `C` | | ✓ | ✓ | Só até `C` |
| Oferta passada | Frequências, assentos por voo, tipo de aeronave até `C`; nº de companhias na rota | ✓ | ✓ | ✓ | Só até `C`, nunca do mês-alvo |
| Qualidade | Meses ausentes nos 12 meses até `C`, idade da rota | ✓ | ✓ | ✓ | Só até `C` |

**Proibidos, pois vêm do próprio mês-alvo:** passageiros, assentos, decolagens, RPK, ASK, combustível, horas, bagagem, horários reais e `load_factor_paid` do período previsto. Também ficam de fora as categorias instáveis `cd_di` e `ds_natureza_tipo_linha`, salvo como filtro de escopo.

**Oferta planejada (cenário opcional).** Os assentos do mês-alvo são uma entrada muito informativa, mas não se sabe se estavam disponíveis. O RSA guarda fotos diárias da malha aprovada, desde 2019, o que permitiria usar a oferta *como conhecida na origem*. Seria um experimento separado, sempre comparado ao cenário sem oferta futura.

**Bagagem total (C′, se aprovado).** Rota x companhia x mês, domésticos de companhias brasileiras, `h` = 1 e 3, treino desde 2018, WAPE e MAE ponderados por passageiros, baseline `T−12`.

## 5. Separação temporal

### Comparação das janelas

Só identificadores e contagens de 2024–2025 foram consultados nesta comparação.

| Janela | Meses disponíveis | Rota x cia x mês | Aeroporto x dia | Peso da pandemia (voos) | Voos de 2023 com rota e companhia conhecidas |
|---|---|---|---|---|---|
| Treino 2003–2022 | 236 de 240 | 398.779 | 1.105.097 | 5,0% | 98,21% |
| Treino 2013–2022 | 116 de 120 | 191.697 | 543.221 | 9,6% | 98,13% |
| Validação 2023 | 12 de 12 | 21.087 | 63.188 | 0 | |
| Teste 2024–2025 | 24 de 24 | 42.556 | 123.502 | 0 | |

Voltar a 2003 dobra as linhas, mas reconhece só 0,08 ponto a mais de voos de 2023. Sozinho, 2003–2012 reconhece apenas 76,7%, e 2017–2022 já chega a 98,0%. O teste 2024–2025 reconhece 95,96% na janela recente e 96,26% na longa.

**Recomendação:** janela recente como principal (treino 2013–2022, validação 2023, teste 2024–2025) e 2003 como experimento na validação. Regra fixada antes de ver resultados: adotar a janela longa só se o erro na validação cair com intervalo de confiança excluindo zero, em todos os horizontes.

### Regras

1. **Atribuição pelo mês-alvo.** Com defasagens de até 24 meses, 2013–2014 serve em boa parte para calcular atributos: os alvos de treino começam em 2014 ou 2015.
2. **Expurgo por horizonte.** Linhas de treino precisam ter `T ≤ C` da primeira origem avaliada. Para o primeiro alvo de validação (2023-01):

| `h` | `k` | Último alvo permitido no treino |
|---|---|---|
| 1 | 3 | 2022-10 |
| 3 | 5 | 2022-08 |
| 6 | 8 | 2022-05 |

3. **Origens móveis.** Validação com 12 meses-alvo; teste com 24, sem ajuste.
4. **Modelo final.** Depois da validação, retreino até 2023 com o mesmo expurgo e congelamento dos hiperparâmetros. Atualização mensal só como linha separada, declarada antes.
5. **Pandemia.** Comparar na validação: manter, reduzir o peso ou excluir de 2020-03 a 2021-12. Nenhum atributo pode dizer "pandemia" no período de avaliação, pois não seria conhecido antes.
6. **Meses ausentes.** Os quatro estão no treino, nenhum em validação ou teste. Enquanto não forem integrados, cada defasagem atinge 4 meses-alvo no total (um por mês ausente), e nessas linhas o atributo fica como desconhecido.

### O conjunto de teste já não é totalmente intocado

**Registro por transparência.** A auditoria mostrou totais anuais de 2024–2025, e este diagnóstico mostrou séries de bagagem por companhia até 2025. Não usei isso para escolher atributos dos módulos A, B e D, mas não posso afirmar que o período é cego. Para bagagem, o contágio é maior.

**Proposta:** manter 2024–2025 como teste final previsto e adicionar **2026-01 a 2026-09 como teste prospectivo**, um período que nunca vimos, publicado na página oficial. Sairia de um único uso, depois de tudo congelado.

### Limitação de revisões

Sem versões históricas, o backtest usa dados já revisados e pode ser otimista nos meses mais recentes. Como `dt_sistema` não foi selecionada na ingestão, ela ainda não está disponível nos Parquets, e os indícios vistos sugerem carga em lote, então não reconstruiria versões. Serei explícito sobre isso nos resultados, e o teste de sensibilidade com `C = O − 3` mede parte do efeito.

## 6. Prevenção de leakage

Vazamentos encontrados nos scripts originais e como cada um será bloqueado:

| Vazamento no código original | Controle |
|---|---|
| Médias históricas sobre toda a base (`02_feature_engineering.py`) | Cálculo por data, com `T ≤ C`, testado |
| `pressao_preco` calculada das próprias entradas | Módulo redefinido; proibidos os dados do mês-alvo |
| `nr_passag_pagos` e `nr_hora_partida_real` como entradas | Lista de permissões vinda de `contract.py`, com erro para colunas `operated` ou `outcome` não defasadas |
| Divisão aleatória, ou por mês sem considerar o ano | Divisão só por mês-alvo |
| Top 20 aeroportos com dados de validação | Seleção só com dados `≤ C` |
| Sem conjunto de teste | Teste usado uma única vez, registrado |

Testes automatizados, escritos antes do treino:

1. **Perturbação do futuro:** alterar todos os valores após `C` não pode mudar nenhum atributo.
2. **Carimbo:** cada atributo guarda o mês mais recente usado, sempre `≤ C`.
3. **Disjunção:** treino, validação e teste não compartilham alvo, e o expurgo é respeitado.
4. **Ajuste só no treino:** codificadores, escalas e limiares são gravados com o período usado.
5. **Máscara de ausentes:** meses ausentes nunca aparecem como zero.
6. **Baselines primeiro:** o relatório só é gerado com o baseline ao lado do modelo.

**Comparação:** intervalos de confiança por bootstrap em blocos de meses-alvo. Se um modelo não superar o baseline na validação, isso será reportado, sem trocar de métrica.

## 7. Limitações que permanecem

- O dicionário oficial não foi encontrado: os significados de "bagagem livre", do relógio e de `kg_peso` são inferidos dos dados.
- A explicação da diferença de passageiros é uma hipótese.
- A comparação com o agregado cobriu 3 companhias, em 8 meses vizinhos.
- Os ZIPs ainda não foram abertos: o esquema, o tamanho e a compatibilidade deles seguem sem verificação.
- Correlação não é causa: a queda da bagagem depois de 2017 coincide com a cobrança, mas estes dados não provam a relação.
