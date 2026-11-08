# Validação da auditoria ML

Branch de entrega: `codex/ml-audit-ifood`, criada de `22a120a5aa94c95810580618531864f9d85f99b9`.
Execução local em 2026-11-08; nenhum deploy, merge ou push.

- Python: **338 passed, 11 skipped**. Skips: CSV real não versionado, painéis e payloads ausentes no checkout isolado. Um aviso de depreciação Starlette/httpx.
- Frontend: **84 passed, 7 skipped**; lint e typecheck (`next typegen && tsc --noEmit`) aprovados.
- Backend: Ruff aprovado; format check de 68 arquivos aprovado; mypy aprovado em 47 arquivos.
- Auditoria dos artefatos: **601 verificações aprovadas**, incluindo métricas, intervalos, horizontes, agregações e integridade SHA-256 de 29 arquivos. Evidência completa em `research/ml-showcase/results/audit.json`.
- Navegador Edge/Playwright: quatro abas e métricas principais conferidas; horizontes 3/6, temas Day/Night, desktop 1440 e mobile 390; nenhum pageerror; largura mobile 390/390 sem overflow. Endpoint local `/v2/models`: HTTP 200. Rotas Analyst bloqueadas no navegador.
- Capturas locais em `data/ml-audit/screenshots/` (ignoradas pelo Git); inspeção visual confirma legibilidade dos indicadores mobile e estrutura desktop. Capturas integrais podem registrar cards durante animações; a captura mobile focada foi feita após estabilização.
- PDFs do relatório técnico e da distribuição web são idênticos, com erratas metodológicas; figuras e resultados históricos preservados.

O teste Python inclui treinos mínimos em fixtures sintéticas temporárias. Nenhum modelo de produção foi retreinado; nenhum target do holdout foi aberto para avaliação. Hash de arquivo não significa leitura de seus targets pelo pipeline de avaliação. O período 2024–2025 já havia sido parcialmente exposto historicamente, conforme decisão 3, e não deve ser chamado de totalmente cego.

Antes da apresentação: distinguir validação de previsão futura; divulgar a limitação do treino histórico D e criar nova versão somente após autorização; não alegar ganho conclusivo de A; tratar Brier como evidência histórica não recalculada; não apresentar ocupação por assentos como RPK/ASK. Módulo C permanece não treinado e pipelines legados não têm resultados reproduzidos nesta auditoria.

Build final: npm run build aprovado; compilação, TypeScript e geração de 12 páginas estáticas concluídos, incluindo /dashboard/ml-studio.
