# Integração v3 + auditoria de Machine Learning

A integração foi autorizada separadamente da auditoria original, incluindo commit, push e Pull Request. O registro anterior em `docs/decisions.md` descreve as restrições da auditoria naquele momento; esta etapa permite publicar a branch de integração, sem merge ou deploy.

## Histórico e preservação

- Base v3: `8d96e3854e5f236b7b119e958957f4fc3a425e84`, confirmada em `origin/feat/ingestion-v2`.
- Auditoria original: `d80482d`, mantida em `codex/ml-audit-ifood`.
- Branch integrada: `codex/integrate-v3-ml-audit`, no worktree `D:\anac-fi-ml-audit`.
- Integração: `git cherry-pick -x d80482d`, gerando `d56d9a3` com a referência ao commit original.
- Nenhum conflito de conteúdo ou resolução manual foi necessário. O commit v3 permanece ancestral; não houve rebase, squash ou alteração do histórico publicado.
- Comparação com v3 confirmou identidade de `src/anac/api/`, `src/anac/agent/`, `deploy/`, `README.md`, `docs/DEPLOYMENT.md`, `pyproject.toml`, `.env.example` e dos testes novos de rankings/rate limiting.
- As alterações ML preservam o conteúdo de `d80482d`, incluindo os seis documentos, catálogo, testes, correções, payload e PDF. São 32 arquivos da auditoria, detalhados em `git show --stat d56d9a3`.
- O arquivo local não rastreado `release-v3.ps1`, no checkout principal, não foi alterado nem incluído. O worktree do Power BI não foi acessado.

## Modelos e evidências

A reconciliação foi repetida na integração: **601 verificações aprovadas**, com SHA-256 dos 29 arquivos de entrada preservados. Pequenas diferenças de arredondamento das somas paralelas ficaram dentro da tolerância numérica; a evidência versionada da auditoria original foi mantida. Relatórios históricos e métricas públicas não foram reescritos.

| Target | Métrica LightGBM | Melhor baseline |
|---|---:|---:|
| A: movimentos | WAPE 10,10% | 10,30% |
| B: ocupação por assentos | MAE ponderado 6,06 pp | 6,54 pp |
| D: passageiros | WAPE 22,24% | 25,31% |
| D: assentos | WAPE 22,40% | 25,73% |

São resultados da validação 2023, não previsões atuais. A não tem ganho conclusivo; D não demonstra ganho em todos os horizontes. A correção do loader de D não retreinou os modelos v1 e seu impacto ainda não foi medido. Nenhum treino real, avaliação do holdout ou chamada à Groq foi executado. Treinos mínimos com fixtures sintéticas fazem parte da suíte de testes.

## Publicação posterior

Este PR tem destino `feat/ingestion-v2`, sem merge na `main`. Não foi executado script de publicação, Docker build/push, alteração no Render/Vercel ou deploy manual. Integrações automáticas do GitHub podem reagir ao push/PR conforme as configurações existentes.

Após revisão e merge, será necessário um novo deploy do frontend para mostrar as explicações e PDF atualizados. Não há mudança no comportamento dos endpoints ou do Analyst em relação à v3; não é necessário um novo deploy de backend para exibir essas melhorias. O código corretivo de treinamento será usado apenas numa futura execução autorizada e versionada.

## Validação da versão consolidada

- Python completo: **368 aprovados, 11 ignorados**, 1 aviso de depreciação Starlette/httpx. Os 11 skips exigem CSV real, painéis ou payloads não presentes no checkout isolado; não foram fabricados nem copiados para fazê-los passar.
- Ruff lint: aprovado em `src`, `tests`, scripts da auditoria e `research/ml-showcase/analysis.py`.
- Ruff format: **71 arquivos aprovados** em `src`, `tests` e scripts da auditoria.
- mypy estrito: **48 arquivos de origem aprovados**.
- Frontend sem API: **84 aprovados e 7 opcionais ignorados**, em 7 arquivos; typecheck e ESLint aprovados. Os cenários opcionais são executados separadamente com API local na validação abaixo.
- `git diff --check`: aprovado. As comparações dos arquivos protegidos da v3 e a ancestralidade de `8d96e38` foram verificadas por Git.
- Frontend com `ANAC_API_URL=http://127.0.0.1:8004`: **91 testes aprovados, nenhum ignorado**, em 7 arquivos. Os sete testes opcionais verificaram payloads, ML Studio, rankings, cobertura, catálogos e Overview com a API v3 integrada e dados analíticos reais somente leitura. Isso não constitui inferência/avaliação do holdout ML; são consultas às séries analíticas históricas já publicadas.
- Build Next.js de produção: aprovado, incluindo compilação, TypeScript e geração de 12 páginas estáticas. O build de teste usou URL local da API via variável de ambiente do processo, sem alteração das configurações publicadas.
- Conferência remota ao final: `origin/feat/ingestion-v2` continua em `8d96e38`.

## Pendências

Revisão e merge deste PR em `feat/ingestion-v2`; redeploy posterior do frontend, mediante autorização; decidir separadamente quando consolidar a branch principal e preparar a apresentação final. Os modelos v1 continuam com suas limitações históricas, e um novo treinamento de D exigirá autorização, nova versão e nova avaliação. Não há falha de teste conhecida bloqueando este PR; os skips Python e o aviso de depreciação estão descritos acima. A integração não revalida o provedor Groq nem a infraestrutura de produção.
