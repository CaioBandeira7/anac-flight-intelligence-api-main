# Roteiro de demonstração (3 minutos)

Para gravação de tela ou apresentação ao vivo. Abra as abas antes: o servidor gratuito do Render hiberna após ~15 minutos sem uso, então acesse `/health` um minuto antes para ele acordar.

| Tempo | Tela | Fala (resumo) |
|---|---|---|
| 0:00–0:20 | Landing (`/`), clicar no boarding pass | "A ANAC publica todas as etapas de voo do Brasil desde 2000, cerca de 20 GB. Construí uma plataforma para transformar isso em respostas corretas e verificáveis." |
| 0:20–0:55 | Overview (`/dashboard`) | "Em 2025: 131,6 milhões de passageiros pagos, +9,7% sobre 2024, ocupação de 82,1%. Cada número traz período e escopo. Meses ausentes na fonte aparecem como lacuna, nunca zero." Alternar DAY/NIGHT. |
| 0:55–1:20 | Routes Explorer (`/dashboard/routes`) | "Rotas têm sentido: CGH→SDU e SDU→CGH são separadas. A ocupação é recalculada como soma de passageiros sobre soma de assentos, nunca média." |
| 1:20–2:05 | ML Studio (`/dashboard/ml-studio`), abas A e D | "Cada modelo é comparado a baselines simples em 2023, dados que ele não viu. No tráfego de aeroportos o LightGBM não venceu com confiança, então a regra simples ficou. Na demanda por rota ele vence: 18,7% de erro contra 24,1% a um mês. Mas subestima cerca de 12% e perde a 6 meses, e isso está na tela." |
| 2:05–2:45 | AI Analyst (`/dashboard/analyst`) | Perguntar "Which were the 5 busiest airports in 2025?". "O modelo só acessa os dados por ferramentas fixas. Cada número é conferido antes de aparecer, e a fonte é anexada pelo código." Mostrar a seção AI Analyst in Action com a verificação independente. |
| 2:45–3:00 | Slide final ou README | "Python, Polars, DuckDB, LightGBM, FastAPI, Next.js e Groq. Publicado, com código aberto e limitações documentadas." |

## Respostas esperadas (conferidas em 2026-11-08)

- 5 aeroportos com mais movimentos em 2025: GRU 287.291 · CGH 186.664 · VCP 122.025 · GIG 117.669 · BSB 116.671 (`/v2/airports`).
- Rota mais movimentada: CGH→SDU, 1.968.523 passageiros pagos, ocupação 76,9% (`/v2/routes`).
- Mercado 2025: 131.593.763 passageiros pagos, variação +9,72% (`/v2/overview`).

## Se algo der errado

- **Analyst responde "free usage limit was reached":** é o limite por minuto da Groq. Espere ~30 s e pergunte de novo, sem enviar várias seguidas.
- **429 "Too many questions from this connection":** é o limite do próprio site (10 por hora). Use as respostas gravadas da seção AI Analyst in Action.
- **Páginas mostram "Couldn't load this data":** a API está acordando. Clique em Retry após 30–60 s.
