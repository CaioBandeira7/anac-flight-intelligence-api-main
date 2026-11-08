# Material visual do portfólio

Gerado em 2026-11-08 a partir do site público e dos arquivos do repositório. Nenhum código de backend, frontend ou ML foi alterado.

## Conteúdo

| Pasta | Arquivos | Uso |
|---|---|---|
| `screenshots/` | 21 capturas reais (18 desktop 1375×674, 3 mobile 494×730), DAY e NIGHT | README, LinkedIn, slides |
| `charts/` | 3 gráficos PNG com fonte no rodapé | Slides, README, posts |
| `cover/` | Capa do GitHub 1280×640 (PT e EN) e imagem de post 1200×627 | Prévia social, LinkedIn |
| `../presentation/` | Apresentação de 10 slides em português e resumo de 4 slides em inglês, em `.pptx` e `.pdf` | Processo seletivo, apresentação ao vivo |
| `../tools/` | Scripts que geraram capturas tratadas, gráficos, capa e slides | Regerar após mudanças |

## Como as capturas foram feitas

Chrome real, janela de desktop, dados carregados da API pública (`ApiDataProvider`, selo "API data"). Antes de cada captura: espera pelo carregamento, barra de rolagem oculta, cursor posicionado em área vazia e depois removido da imagem. A pergunta ao AI Analyst foi feita ao vivo ("Which were the 5 busiest airports in 2025?"); a resposta foi conferida com `/v2/airports`.

## O que foi verificado

| Informação | Valor | Conferido contra |
|---|---|---|
| Passageiros pagos 2025 | 131.593.763 (+9,72%) | `/v2/overview` e soma mensal de `/v2/analytics/routes/monthly` |
| Voos 2025 / ocupação | 976,4 mil / 82,1% | `/v2/overview` |
| Série anual 2000–2025 | 26 totais anuais | soma dos 308 meses de `/v2/analytics/routes/monthly` |
| Anos com mês ausente | 2015, 2016, 2018, 2020 | `/v2/analytics/coverage` (`absent_months`) |
| Top 5 aeroportos | GRU 287.291 … BSB 116.671 | `/v2/airports` |
| Top rota | CGH→SDU 1.968.523, 76,9% | `/v2/routes` e Routes Explorer |
| Linhas da ingestão | 22.120.241, 1,18 GB, 8 min, pico 2,37 GB | `docs/ingestion.md` |
| Tabelas analíticas | 3 dimensões, 4 fatos; `fact_route_month` 405.134 linhas | `/v2/analytics/coverage` |
| Métricas de ML (A, B, D) | WAPE, MAE e intervalos | `research/ml-showcase/REPORT.md` e `results/analysis.json` |
| D por horizonte | 18,74 / 21,31 / 26,71% vs 24,07 / 25,35 / 25,09% | `results/analysis.json`, `tasks.d_pax.by_horizon` |
| Testes do backend | 364 passando | execução do dono em 2026-11-08 (`release-v3.ps1`) |
| Limites do Analyst | 10/hora por visitante, 200/dia | variáveis do Render e `docs/DEPLOYMENT.md` |

Não verificado por mim: os 81 testes de frontend citados em `CASE_STUDY.md` (não executados nesta rodada) e a separação do limite por visitante vindo de redes diferentes (testada só de uma rede).

## Atualizar depois da integração do Codex

- **Slides 7 e 8, gráficos de ML e textos de LinkedIn/currículo:** se a auditoria de ML (`codex/ml-audit-ifood`) mudar alguma métrica, intervalo ou conclusão, regere `charts/` e o deck com `tools/` e revise os números citados. Até a auditoria ser publicada, os materiais usam só os resultados em `research/ml-showcase/`.
- **Capturas do ML Studio:** refazer se a página mudar.
- **Contagem de testes** (364): atualizar com a execução da versão consolidada.
- **README principal:** colar o bloco de `../README_GALLERY.md` na versão consolidada.
- **Links:** se o domínio da Vercel ou do Render mudar, atualizar slides 1 e 10, `LINKEDIN_PT.md`, `PORTFOLIO_EN.md`, `CV.md` e a capa.
