# LinkedIn — português, versão secundária

Construí o ANAC Flight Intelligence para transformar 22.120.241 registros de aviação em análises verificáveis: ingestão auditada em Parquet, camada analítica de sete tabelas, dashboard Next.js e um AI Analyst com ferramentas fixas via Groq.

O aprendizado mais importante foi saber onde a evidência termina. O ganho do modelo A é inconclusivo, então o baseline permanece. A auditoria encontrou meses ausentes tratados como zero no treino histórico de D; o loader foi corrigido, mas os modelos não foram retreinados. O holdout 2024–2025 foi parcialmente exposto, porém não pontuado. C não foi treinado. O site mostra avaliação histórica, não previsão futura.

A verificação numérica do Analyst é heurística: não garante toda associação entre número, entidade e métrica. Os limites são contadores em memória por processo.

Validação: 368 testes Python aprovados, 11 ignorados; 91 frontend aprovados. Direcionei escopo e revisão com implementação assistida por Claude Code e Codex, sob regras escritas e aprovação humana.

Demo: https://anac-flight-intelligence-api-main.vercel.app/dashboard
Código: https://github.com/CaioBandeira7/anac-flight-intelligence-api-main

#DataScience #MachineLearning #GenAI #Python #DadosAbertos

[Texto principal em inglês](LINKEDIN_EN.md) · [Validação](VALIDATION.md). Rascunho; nenhum post foi publicado.
