# Parecer técnico de encerramento

Data: 2026-11-08. Versão consolidada: branch `codex/integrate-v3-ml-audit`, PR #1 para `feat/ingestion-v2`. Base publicada `8d96e38`; cherry-pick rastreável da auditoria `d80482d` em `d56d9a3`; validação registrada em `6cea8f9`. A integração já existente foi verificada e preservada, sem duplicação de branch ou de PR.

## Parecer

**Pronto para avaliação técnica como portfólio**, com revisão/merge do PR e publicação posterior do frontend ainda pendentes. Não apresentar como serviço de previsão operacional ou como sistema de produção com garantias de escala. Os problemas metodológicos conhecidos estão expostos e os resultados históricos são verificáveis. Não é necessário adicionar funcionalidades para a candidatura.

## Revisão final por camada

| Camada | Evidência e conclusão | Limite da verificação |
|---|---|---|
| Ingestão | `pipeline.py`, `validation/report.py`, testes de parsing/chunking/pipeline e `reports/ingestion/quality_report.json`: processamento por blocos, publicação atômica, retomada e reconciliação. As identidades do relatório foram conferidas: 22.120.241 linhas publicadas, 308 meses, nenhuma partição incorreta. | Relatório histórico; o CSV de cerca de 20 GB não foi reprocessado nesta revisão. Fingerprints históricos não equivalem a hash completo de todo o dataset. |
| Analytics | `reports/analytics/validation.json`: status passed e 308 meses comparados com a fonte. A suíte frontend com API local verificou períodos, lacunas, direções, rankings, market share e catálogos. | Não foi reconstruído o pacote analítico; sua validação completa é evidência histórica. |
| ML | Quatro LightGBM, dez referências de baseline, reconciliação de 601 checks e hashes de 29 arquivos. Gráficos e payloads comparados com resultados salvos de seleção de 2023. | Nenhum refit real, treinamento corrigido de D ou avaliação do holdout. |
| Dashboard/ML Studio | 91 testes frontend com a API integrada local; typecheck, lint e build aprovados. Textos, unidades, escopo dos gráficos e PDF auditados. | Não foi repetida a revisão visual já registrada em VALIDATION.md, pois o código é o mesmo. |
| AI Analyst | Código v3 preservado, testes com mocks de LLM, rankings e limites incluídos na suíte consolidada. Verificador numérico e respostas de falha presentes. | Não se chamou Groq nem se revalidou a disponibilidade do provedor. O verificador pode aceitar um número real associado à entidade errada. |
| Endpoints/CORS | API e configurações idênticas à v3; contratos e testes da API na suíte completa. CORS usa `ANAC_CORS_ORIGINS`; consultas locais de dados passaram. | Variáveis reais do Render/Vercel não foram alteradas nem inspecionadas nesta etapa. CORS não é autenticação ou proteção contra clientes fora do navegador. |
| Rate limiting | Controles por cliente e quota diária UTC, lock para concorrência, rejeição 429 antes da chamada LLM, Retry-After e testes. X-Forwarded-For não é usado; header de edge exige configuração. | Estado em memória por processo, reinicia com o serviço e não compartilha quotas entre réplicas. Evicção no limite de clientes pode perder contagens individuais; quota global continua por processo. |
| Credenciais | 361 arquivos rastreados examinados para padrões específicos de tokens Groq/GitHub/AWS e chaves privadas: nenhuma ocorrência. Nenhum `.env` privado rastreado; regras Git verificadas para env, dados, modelos, node_modules e builds. Allowlists específicas dos Dockerfiles excluem credenciais. | Busca por padrões no snapshot atual, não certificação de segurança nem varredura completa de histórico/dependências. Nenhuma credencial foi exibida ou copiada. |

## Validação executada na integração

Os checks abaixo foram executados nesta mesma integração, antes deste parecer; não foram repetidos por uma mudança exclusivamente documental. O código validado continua igual.

- **Python: 368 aprovados, 11 ignorados**, não 364. A contagem efetivamente observada prevalece sobre a estimativa do contexto. Skips: CSV real/painéis/payloads ausentes no checkout isolado. Um aviso Starlette/httpx de depreciação.
- **Frontend: 91 aprovados**, nenhum ignorado, com API local integrada. Execução inicial sem API: 84 aprovados e 7 opcionais ignorados.
- **Ruff lint e formatação aprovados**; formatação de 71 arquivos. **mypy: 48 arquivos aprovados**.
- **ESLint, TypeScript e build Next.js aprovados**, com 12 páginas estáticas geradas.
- **601 checks ML aprovados** e integridade dos artefatos preservada. `git diff --check` aprovado.
- Os testes de treino usam somente pequenas fixtures sintéticas temporárias. Consultas analíticas de 2024–2025 não são avaliação de targets do holdout ML.

## Limitações que devem acompanhar a apresentação

1. A: WAPE LightGBM 10,10% contra baseline 10,30%; diferença com intervalo incluindo zero. Manter baseline como método selecionado.
2. B: MAE ponderado por assentos 6,06 pp contra 6,54 pp; ocupação é passageiros pagos/assentos, não RPK/ASK. O novo bias ponderado não substitui silenciosamente o campo relativo legado.
3. D: WAPE histórico de passageiros 22,24% e assentos 22,40%. Treino v1 incluiu targets de meses globalmente ausentes preenchidos como zero; o loader foi corrigido, mas os modelos históricos não foram retreinados. Não atribuir qualquer melhora à correção. Há bias e ausência de ganho demonstrado em todos os horizontes.
4. Holdout 2024–2025 não pontuado, mas parcialmente exposto historicamente; não chamar de totalmente cego. Validação 2023 contém só 12 clusters mensais e não comprova estabilidade em outros anos.
5. C: não treinado, sem métricas a apresentar. Os quatro pipelines legados foram inventariados sem reprodução de resultados.
6. Não existe endpoint operacional de previsão futura. As telas mostram avaliação histórica; ganho de validação, intervalos de bootstrap e importância por gain não provam causalidade, certeza futura ou retorno comercial.
7. Quatro meses ausentes são desconhecidos, não zero. Dados revisados não oferecem vintages completos de disponibilidade histórica. Brier secundário permanece evidência histórica não reproduzida independentemente.

## Entrega e publicação

Os seis documentos técnicos solicitados e o catálogo permanecem em `docs/ml/`: MODEL_CATALOG, EXPERIMENT_RESULTS, VISUALIZATION_CATALOG, PREDICTION_GUIDE, ML_ARCHITECTURE e INTERVIEW_GUIDE. Contagens: **26 gráficos web e 37 figuras de relatório**, além de tabelas, KPIs e painéis de registro.

O PR inclui a auditoria integral e os registros de integração/encerramento. Não houve conflito manual nem alteração das funcionalidades v3. O worktree Power BI não foi acessado, o arquivo local `release-v3.ps1` no checkout principal foi preservado e a main não foi alterada.

Após aprovação e merge, publicar apenas o **frontend Next.js `web/`** para expor explicações, tooltips, payload `web/public/ml/showcase.json` e PDF `web/public/ml/report.pdf`. A integração não altera runtime dos endpoints/Analyst da v3; novo deploy de backend ou nova imagem Docker não é necessário para essas melhorias. A correção de treinamento está no repositório e será usada numa execução futura separadamente autorizada. Não se executou deploy manual nem se alterou Render/Vercel; previews automáticos podem ocorrer pelo vínculo GitHub existente.

Pendências para o congelamento de código: revisão/merge do PR em feat/ingestion-v2 e decisão de publicação do frontend. Pendências metodológicas documentadas não exigem nova funcionalidade para a apresentação, mas impedem alegações de previsão operacional ou de performance corrigida de D. Antes da entrevista, conferir os links públicos, preparar demonstração sem depender de disponibilidade contínua da API e usar INTERVIEW_GUIDE para explicar também as limitações. Uma validação real de Groq continua dependendo de autorização de chamada.
