# ANAC Flight Intelligence 2.0 — Web

Frontend cinematográfico do ANAC Flight Intelligence: landing com céu e nuvens em camadas, transição de decolagem e dashboard de inteligência aeronáutica.

> **Todos os dados exibidos nesta entrega são DEMO** (sintéticos, determinísticos). Nenhuma métrica de ML é simulada — os modelos aparecem como *Awaiting training* até a API reportar avaliações reais.

## Stack

- Next.js 16 (App Router, Turbopack, Cache Components) · React 19 · TypeScript
- Tailwind CSS v4 · estrutura shadcn/ui (`components.json`, `lib/utils.ts`, `components/ui/button.tsx`)
- Framer Motion · lucide-react · fontes locais (Geist + Instrument Serif, sem rede no build)
- Vitest + Testing Library

## Rodar

```bash
cd web
npm install
npm run dev          # http://localhost:3000
npm run build && npm start
npm test             # vitest
npm run lint && npm run typecheck
```

Fonte de dados (`.env.local`, veja `.env.example`):

```
NEXT_PUBLIC_DATA_SOURCE=mock   # mock (DEMO, padrão) | api
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Estrutura

```
app/
  page.tsx                      Landing (READY TO FLY?)
  dashboard/                    Shell + Overview + módulos (placeholders navegáveis)
components/
  ui/hero-section-3.tsx         ScrollFlyIn adaptado + <FlyingPlane/> compartilhado
  landing/                      céu, hero, decolagem, scrollytelling
  dashboard/                    shell, gráficos, overview
lib/
  motion/flight-path.ts         ÚNICA fonte da trajetória do avião (scroll e decolagem)
  data/contracts.ts             contratos TypeScript
  data/mock-provider.ts         MockDataProvider (DEMO)
  data/api-provider.ts          ApiDataProvider (FastAPI)
public/images/
  airliner.svg                  avião (arte original, sem marca)
  sky/*.webp                    camadas de nuvens geradas proceduralmente (~120 KB no total)
```

## Como a experiência funciona

- **Um sistema de movimento.** `flightFrame(progress, viewport, mode)` calcula posição, escala, rotação, opacidade e blur. O `ScrollFlyIn` alimenta `progress` com `useScroll`; a decolagem alimenta com um `animate()` linear. Mesma lógica, dois drivers.
- **Uma timeline de decolagem.** Get Started anima um único `MotionValue` 0→1 (3,4 s). Texto, nuvens (aceleram e caem — câmera subindo), avião, escurecimento e HUD derivam dele. No fim, `router.push('/dashboard')` (sem reload); o dashboard abre no mesmo quadro navy + HUD e dissolve para o produto.
- **Performance.** Nuvens são bitmaps WebP leves deslizando por `@keyframes` (só `transform`, no compositor). Parallax e transições usam apenas `transform`/`opacity`. O overlay de decolagem só é montado ao clicar. Viewport em motion values → resize não re-renderiza React.
- **ScrollFlyIn.** Mantém a ideia original (wrapper alto, sticky, `useScroll`/`useTransform`, janela 0.1–0.8 e opacidade `[0,1,1,0]`). Sem `window.innerWidth` no render (SSR-safe), imagem local com fallback, stage com `overflow: hidden` (sem scroll horizontal).
- **Acessibilidade.** Skip links, "Skip intro" direto ao dashboard, foco visível, `prefers-reduced-motion` (sem trajetória do avião; decolagem vira fade de 450 ms), gráfico navegável por setas + tabela para leitores de tela, `aria-live` na decolagem.

## Contrato esperado da API (v2)

| Método | Endpoint | Tipo |
|---|---|---|
| GET | `/health` | `HealthStatus` (já existe) |
| GET | `/v2/overview` | `OverviewData` |
| GET | `/v2/airports` | `AirportStat[]` |
| GET | `/v2/routes` | `RouteStat[]` |
| GET | `/v2/models` | `ModelCard[]` |
| GET | `/v2/datasets` | `DatasetInfo[]` |

Aceita payload puro ou envelope `{ data, meta }`. Se o backend servir amostras, basta enviar `meta.isDemo: true` que o selo DEMO aparece. Trocar `NEXT_PUBLIC_DATA_SOURCE=api` não exige mudar nenhum componente.

Observação: a API Python precisará de CORS para a origem do frontend (ex.: `http://localhost:3000`).

## Próximas entregas

Airports Intelligence, Routes Explorer, Airlines Analytics, ML Studio (incluindo `POST /prever`) e Data & Methodology já estão na navegação, com o conteúdo planejado descrito em cada página.
