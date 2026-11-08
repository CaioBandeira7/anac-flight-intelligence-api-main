# Descrição para currículo

## Português (3 linhas)

**ANAC Flight Intelligence** · Python, Polars, DuckDB, LightGBM, FastAPI, Next.js, Groq · [anac-flight-intelligence-api-main.vercel.app](https://anac-flight-intelligence-api-main.vercel.app)
- Plataforma de dados e ML sobre 22,1 mi de registros de voo da ANAC (2000–2025): ingestão auditada em Parquet, esquema estrela, API somente leitura em Docker (Render) e dashboard Next.js (Vercel).
- Modelos LightGBM validados contra baselines com IC 95%; na demanda por rota, WAPE de 18,7% vs 24,1% a 1 mês. Onde o ganho não foi conclusivo, o baseline foi mantido.
- AI Analyst com LLM (Groq) restrito a ferramentas fixas, verificação numérica das respostas e limite de uso por visitante.

## English (3 lines)

**ANAC Flight Intelligence** · Python, Polars, DuckDB, LightGBM, FastAPI, Next.js, Groq · [anac-flight-intelligence-api-main.vercel.app](https://anac-flight-intelligence-api-main.vercel.app)
- Data and ML platform on 22.1M ANAC flight records (2000–2025): audited Parquet ingestion, star schema, read-only API in Docker (Render) and a Next.js dashboard (Vercel).
- LightGBM models validated against baselines with 95% intervals; route demand WAPE 18.7% vs 24.1% one month ahead. Where the gain was not conclusive, the baseline was kept.
- LLM analyst (Groq) restricted to fixed tools, with numeric verification of answers and per-visitor rate limits.

## Uma linha (formulários e perfil)

Plataforma de dados, ML e IA generativa sobre a aviação brasileira, publicada e com cada número verificável.

## Para o processo iFood GenAI Internship

Pontos do projeto que conversam com uma vaga de IA generativa, todos verificáveis no repositório ou no site:

- **LLM com ferramentas (tool calling):** o analista só acessa dados por 5 funções fixas e validadas (`src/anac/agent/tools.py`); argumentos fora do esquema são recusados.
- **Controle de alucinação:** cada número da resposta é conferido contra o resultado da ferramenta que o originou (`src/anac/agent/verification.py`); rascunhos reprovados são reescritos uma vez e, se falharem de novo, recusados.
- **Avaliação:** casos reais gravados e conferidos por um caminho independente (`docs/portfolio/ANALYST_DEMO.md`).
- **Produção:** chave apenas no servidor, limite de 10 perguntas por hora por visitante e 200 por dia, 429 com `Retry-After`, IP do cliente lido do cabeçalho da borda (Cloudflare); um valor enviado pelo próprio visitante é bloqueado antes de chegar à API (testado em 2026-11-08).
- **Honestidade metodológica no ML:** baseline mantido onde o modelo não vence; viés e horizontes ruins documentados.
