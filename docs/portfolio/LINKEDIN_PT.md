# Post para o LinkedIn (português)

Imagem sugerida: `assets/cover/linkedin-post-1200x627.jpg`. Carrossel opcional: as 10 páginas de `presentation/anac-flight-intelligence-apresentacao.pdf`.

---

A ANAC publica todas as etapas de voo do Brasil desde 2000. São cerca de 20 GB de dados abertos, e usá-los corretamente é mais difícil do que parece.

Voos, voos de passageiros e movimentos de aeronaves são contagens diferentes. Rotas têm sentido. Taxa de ocupação não se calcula por média. E quatro meses simplesmente não existem na fonte, o que não pode virar zero num gráfico.

Construí o ANAC Flight Intelligence para fazer esse trabalho uma vez, validar e mostrar cada número com período, unidade e fonte:

✈️ Ingestão auditada de 22,1 milhões de linhas (2000–2025) em Parquet, com releitura independente do CSV.
📊 Dashboard em Next.js com mercado, aeroportos, rotas e empresas. Em 2025: 131,6 milhões de passageiros pagos (+9,7%) e ocupação de 82,1%.
🤖 Modelos LightGBM comparados a baselines simples em dados de 2023 que eles não viram. Um modelo só é adotado se vencer o melhor baseline com intervalo de confiança de 95% que exclui zero. Na demanda por rota, 1 mês à frente, o erro (WAPE) cai de 24,1% para 18,7%. No tráfego de aeroportos o ganho não foi conclusivo, então a regra simples ficou.
💬 Um AI Analyst (Groq) que responde em linguagem natural usando só ferramentas fixas e somente leitura. Cada número da resposta é conferido contra os dados antes de aparecer.

Também deixei as limitações à vista: o modelo de demanda subestima cerca de 12%, perde do baseline a 6 meses, e o teste final em 2024–2025 ainda não foi executado.

Está no ar: anac-flight-intelligence-api-main.vercel.app
Código: github.com/CaioBandeira7/anac-flight-intelligence-api-main

Stack: Python, Polars, DuckDB, LightGBM, FastAPI, Docker, Next.js, TypeScript e Groq. Construído com Claude Code e Codex, sob regras escritas e com cada etapa aprovada por mim.

#DataScience #MachineLearning #GenAI #Aviação #DadosAbertos #Python

---

## Versão curta (comentário, story ou bio do projeto)

ANAC Flight Intelligence: 22,1 milhões de registros de voo (2000–2025) viram um dashboard, modelos comparados a baselines e um AI Analyst que confere cada número. No ar em anac-flight-intelligence-api-main.vercel.app.

## Conferência dos números deste texto

| Afirmação | Fonte |
|---|---|
| 22,1 mi linhas, 20 GB, 2000–2025 | `docs/ingestion.md` (execução completa: 22.120.241 linhas) |
| 131,6 mi passageiros, +9,7%, 82,1% | `/v2/overview` da API pública, 2026-11-08 |
| WAPE 18,7% vs 24,1% (D, 1 mês) | `research/ml-showcase/results/analysis.json`, `tasks.d_pax.by_horizon` |
| A sem ganho conclusivo, viés −12%, 6 meses pior | `research/ml-showcase/REPORT.md`, tabela-resumo |
| Teste 2024–2025 não executado | `AGENTS.md`, `REPORT.md` seção 6.4 |
