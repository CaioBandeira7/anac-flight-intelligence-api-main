const pptxgen = require("pptxgenjs");
const { applyTheme } = require("/root/.claude/skills/synced/d491bc66-f4ab-4915-9229-3011731b1fa8_a3402b2c-6f64-422f-9a6f-770ec68edc4d/pptx/scripts/apply_theme.js");
const path = require("path");
const A = process.argv[2]; const OUT = process.argv[3]; const LANG = process.argv[4] || "pt";
const img = (p) => path.join(A, p);
const THEME = { name: "ANAC Flight Intelligence", headFontFace: "Calibri", bodyFontFace: "Calibri",
  colors: { dk1: "16213A", lt1: "FFFFFF", dk2: "0E2A5C", lt2: "EAF1FC", accent1: "1F5FD6", accent2: "7FB0EA",
    accent3: "9AA6B8", accent4: "0F9D7A", accent5: "C2410C", accent6: "56627A", hlink: "1F5FD6", folHlink: "0E2A5C" } };
const pres = new pptxgen(); pres.layout = "LAYOUT_WIDE"; pres.theme = { headFontFace: "Calibri", bodyFontFace: "Calibri" };
pres.title = LANG === "pt" ? "ANAC Flight Intelligence — apresentação" : "ANAC Flight Intelligence — summary";
pres.author = "Caio Bandeira";
const C = pres.SchemeColor;
const W = 13.333, H = 7.5, M = 0.6;
pres.defineSlideMaster({ title: "TITLE_DARK", background: { color: THEME.colors.dk2 }, objects: [],
  });
pres.defineSlideMaster({ title: "CONTENT", background: { color: "FFFFFF" },
  objects: [{ placeholder: { options: { name: "title", type: "title", x: M, y: 0.4, w: W - 2 * M, h: 0.8, fontSize: 34, bold: true, color: C.text2, valign: "top", align: "left", margin: 0 }, text: "" } },
            { text: { text: "ANAC Flight Intelligence", options: { x: M, y: H - 0.45, w: 5, h: 0.3, fontSize: 10, color: C.accent6, margin: 0 } } }],
  slideNumber: { x: W - M - 0.6, y: H - 0.45, w: 0.6, h: 0.3, fontSize: 10, color: C.accent6, align: "right" } });

function shadow() { return { type: "outer", blur: 8, offset: 3, angle: 90, color: "0E2A5C", opacity: 0.18 }; }
function shot(s, file, x, y, w, ratio = 674 / 1375, name) {
  s.addImage({ path: img(file), x, y, w, h: w * ratio, rounding: false, shadow: shadow(), objectName: name || file, altText: name || file });
}
function card(s, x, y, w, h, title, body, opts = {}) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: opts.fill || "EAF1FC" }, line: { color: opts.fill || "EAF1FC" }, objectName: "card " + title });
  s.addText(title, { x: x + 0.25, y: y + 0.18, w: w - 0.5, h: 0.4, fontSize: 17, bold: true, color: C.text2, margin: 0, isTextBox: true });
  s.addText(body, { x: x + 0.25, y: y + 0.62, w: w - 0.5, h: h - 0.75, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true, paraSpaceAfter: 4 });
}
function stat(s, x, y, w, big, label, color) {
  s.addText(big, { x, y, w, h: 0.8, fontSize: 40, bold: true, color: color || C.accent1, margin: 0, isTextBox: true });
  s.addText(label, { x, y: y + 0.8, w, h: 0.6, fontSize: 13, color: C.accent6, margin: 0, valign: "top", isTextBox: true });
}
function bullets(items, size = 15) { return items.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < items.length - 1, fontSize: size, paraSpaceAfter: 6 } })); }
function caption(s, t, y) { s.addText(t, { x: M, y: y || H - 0.85, w: W - 2 * M, h: 0.3, fontSize: 10, color: C.accent6, margin: 0, isTextBox: true }); }
const T = (pt, en) => (LANG === "pt" ? pt : en);
const LIVE = "anac-flight-intelligence-api-main.vercel.app";

// ---------- 1. Title
{
  const s = pres.addSlide({ masterName: "TITLE_DARK" });
  s.addImage({ path: img("cover/cover-github-1280x640" + (LANG === "en" ? "-en" : "") + ".jpg"), x: 0, y: 0, w: W, h: W / 2, objectName: "cover" });
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: W / 2, w: W, h: H - W / 2, fill: { color: THEME.colors.dk2 }, line: { color: THEME.colors.dk2 } });
  s.addText(T("Caio Bandeira · Ciência de Dados e Machine Learning (UniCEUB)", "Caio Bandeira · Data Science and Machine Learning (UniCEUB)"),
    { x: M, y: W / 2 + 0.2, w: 8, h: 0.35, fontSize: 15, color: "FFFFFF", margin: 0, isTextBox: true });
  s.addText(LIVE + "  ·  github.com/CaioBandeira7/anac-flight-intelligence-api-main",
    { x: M, y: W / 2 + 0.55, w: W - 2 * M, h: 0.3, fontSize: 12, color: "CADCFC", margin: 0, isTextBox: true });
  s.addNotes(T("Uma plataforma de dados e ML sobre os microdados públicos da ANAC, publicada e verificável.", "A data and ML platform over ANAC's open microdata, live and verifiable."));
}
if (LANG === "pt") {
// ---------- 2. Problem
{
  const s = pres.addSlide({ masterName: "CONTENT" }); s.addText("Problema e oportunidade", { placeholder: "title" });
  s.addText("A ANAC publica todas as etapas de voo do Brasil desde 2000: cerca de 20 GB de dados abertos. Usá-los corretamente é difícil.",
    { x: M, y: 1.25, w: W - 2 * M, h: 0.6, fontSize: 17, color: C.text1, margin: 0, isTextBox: true });
  const items = [["Contagens diferentes", "Voos, voos de passageiros e movimentos (pousos + decolagens) não são a mesma coisa."],
    ["Rotas têm sentido", "CGH→SDU e SDU→CGH são linhas separadas."],
    ["Ocupação não se média", "Load factor = Σ passageiros pagos / Σ assentos, recalculado em cada recorte."],
    ["Meses ausentes", "2015-08, 2016-02, 2018-07 e 2020-08 não existem na fonte: são lacunas, nunca zero."]];
  items.forEach((it, i) => card(s, M + (i % 2) * 6.15, 2.05 + Math.floor(i / 2) * 1.75, 5.95, 1.55, it[0], it[1]));
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: 5.7, w: W - 2 * M, h: 0.85, rectRadius: 0.12, fill: { color: THEME.colors.dk2 }, line: { color: THEME.colors.dk2 } });
  s.addText([{ text: "Oportunidade: ", options: { bold: true } }, { text: "fazer esse trabalho uma vez, validar, e mostrar cada número com período, escopo, unidade e fonte." }],
    { x: M + 0.3, y: 5.7, w: W - 2 * M - 0.6, h: 0.85, fontSize: 16, color: "FFFFFF", margin: 0, valign: "middle", isTextBox: true });
}
// ---------- 3. Data
{
  const s = pres.addSlide({ masterName: "CONTENT" }); s.addText("Fonte dos dados e dimensão do projeto", { placeholder: "title" });
  stat(s, M, 1.35, 2.9, "20 GB", "CSV bruto da ANAC, nunca modificado");
  stat(s, M, 2.55, 2.9, "22,1 mi", "linhas lidas (22.120.241), nenhuma rejeitada");
  stat(s, M, 3.75, 2.9, "308", "meses com dados, 2000-01 a 2025-12 (4 ausentes)");
  stat(s, M, 4.95, 2.9, "1,18 GB", "em Parquet, ingestão completa em 8 min");
  s.addImage({ path: img("charts/annual-paid-passengers-2000-2025.png"), x: 3.75, y: 1.45, w: 9.0, h: 9.0 * 857 / 1900, objectName: "annual passengers chart", altText: "Passageiros pagos por ano 2000–2025" });
  s.addText("Camada analítica: esquema estrela com 3 dimensões e 4 tabelas fato (ex.: fact_route_month com 405.134 linhas).",
    { x: 3.75, y: 6.05, w: 9.0, h: 0.5, fontSize: 13, color: C.text1, margin: 0, isTextBox: true });
  caption(s, "Fontes: docs/ingestion.md (execução completa) e /v2/analytics/coverage da API pública, consultados em 2026-11-08.");
}
// ---------- 4. Architecture
{
  const s = pres.addSlide({ masterName: "CONTENT" }); s.addText("Arquitetura da solução", { placeholder: "title" });
  const steps = [["CSV ANAC", "20 GB, 2000–2025"], ["anac-ingest", "Parquet auditado, retomável"], ["anac-features", "point-in-time, splits cronológicos"],
    ["anac-models", "LightGBM vs baselines, congelados"], ["anac-analytics", "esquema estrela (DuckDB)"]];
  const bw = 2.2, gap = 0.29, y = 1.55;
  steps.forEach((st, i) => {
    const x = M + i * (bw + gap);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: bw, h: 1.25, rectRadius: 0.12, fill: { color: i === 0 ? "EAF1FC" : "FFFFFF" }, line: { color: THEME.colors.accent1, width: 1.25 }, objectName: "step " + st[0] });
    s.addText([{ text: st[0], options: { bold: true, fontSize: 15, color: C.text2, breakLine: true } }, { text: st[1], options: { fontSize: 12, color: C.accent6 } }],
      { x: x + 0.12, y, w: bw - 0.24, h: 1.25, align: "center", valign: "middle", margin: 0, isTextBox: true });
    if (i < steps.length - 1) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + bw + 0.04, y: y + 0.5, w: gap - 0.08, h: 0.25, fill: { color: THEME.colors.accent1 }, line: { color: THEME.colors.accent1 } });
  });
  const lower = [["API FastAPI", "Somente leitura · /v2/* e /v2/analytics/*\nDocker no Render (imagem v3)"],
    ["Dashboard Next.js 16", "React 19 · TypeScript · Tailwind 4\nVercel, temas DAY/NIGHT"],
    ["AI Analyst", "Groq (openai/gpt-oss-120b)\n5 ferramentas fixas · verificador numérico"]];
  lower.forEach((l, i) => card(s, M + i * 4.1, 3.45, 3.9, 1.75, l[0], l[1], { fill: i === 0 ? "EAF1FC" : "F3F6FB" }));
  s.addText("Regras escritas para os agentes (AGENTS.md): dados nunca inventados, contrato da API espelhado em TypeScript, cada área com dono.",
    { x: M, y: 5.55, w: W - 2 * M, h: 0.6, fontSize: 14, color: C.text1, margin: 0, isTextBox: true });
  caption(s, "Detalhes: README.md (Architecture) e docs/DEPLOYMENT.md.");
}
// ---------- 5. Data engineering
{
  const s = pres.addSlide({ masterName: "CONTENT" }); s.addText("Engenharia e processamento dos dados", { placeholder: "title" });
  card(s, M, 1.45, 3.9, 2.35, "Ingestão em blocos", "151 blocos, 42 MB/s, pico de 2,37 GB de RAM. Para com segurança se a memória passar do limite.");
  card(s, M + 4.1, 1.45, 3.9, 2.35, "Auditoria independente", "Script separado relê o CSV com DuckDB e outro parser; os totais batem com o pipeline.");
  card(s, M + 8.2, 1.45, 3.9, 2.35, "Sem vazamento", "Atributos point-in-time, atraso de publicação de 2 meses, fronteiras purgadas; testes embaralham o futuro.");
  card(s, M, 4.0, 3.9, 1.95, "Regras de dados", "Escopo de passageiros por etapa, rotas direcionadas, meses ausentes como lacunas.");
  card(s, M + 4.1, 4.0, 3.9, 1.95, "Bugs encontrados", "A regra original marcava 100% das linhas como internacionais; corrigido para cruzar fronteira.");
  card(s, M + 8.2, 4.0, 3.9, 1.95, "Qualidade", "364 testes automatizados no backend (pytest), ruff e mypy estrito, em 2026-11-08.");
  caption(s, "Fontes: docs/ingestion.md, reports/ingestion/INGESTION_REPORT.md, docs/features.md.");
}
// ---------- 6. Dashboard
{
  const s = pres.addSlide({ masterName: "CONTENT" }); s.addText("Dashboard analítico", { placeholder: "title" });
  shot(s, "screenshots/dashboard-overview-kpis.jpg", M, 1.4, 6.0, undefined, "Overview com KPIs");
  shot(s, "screenshots/routes-explorer-ranking.jpg", M + 6.25, 1.4, 6.0, undefined, "Ranking de rotas");
  s.addText(bullets(["Mercado, aeroportos, rotas e empresas para qualquer período, comparado ao mesmo período do ano anterior",
    "2025: 131,6 mi de passageiros pagos (+9,7%), 976,4 mil voos, ocupação de 82,1%",
    "Cada tela trata carregamento, erro e vazio; meses ausentes aparecem como lacuna"], 14),
    { x: M, y: 4.55, w: W - 2 * M, h: 1.6, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  caption(s, "Capturas reais do site público em 2026-11-08 (tema DAY).");
}
// ---------- 7. ML
{
  const s = pres.addSlide({ masterName: "CONTENT" }); s.addText("Modelos de Machine Learning e baselines", { placeholder: "title" });
  s.addImage({ path: img("charts/ml-validation-2023-vs-baselines.png"), x: M, y: 1.3, w: 10.2, h: 10.2 * 935 / 2376, objectName: "ml chart", altText: "Validação 2023: LightGBM vs melhor baseline" });
  s.addText(bullets(["Splits cronológicos; validação em 2023, dados não vistos no treino",
    "Adotado só se vencer o melhor baseline com IC 95% que exclui zero (bootstrap em blocos)"], 14),
    { x: M, y: 5.45, w: 5.9, h: 1.0, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  s.addText(bullets(["Módulo A: o baseline é mantido, porque o ganho do LightGBM não é conclusivo",
    "Módulo C (bagagem) não foi treinado"], 14),
    { x: M + 6.2, y: 5.45, w: 5.9, h: 1.0, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  caption(s, "Fonte: research/ml-showcase/REPORT.md. Resultados de validação, não previsões; não há endpoint de previsão.");
}
// ---------- 8. Results and limitations
{
  const s = pres.addSlide({ masterName: "CONTENT" }); s.addText("Resultados reais e limitações metodológicas", { placeholder: "title" });
  s.addImage({ path: img("charts/ml-model-d-error-by-horizon.png"), x: M, y: 1.35, w: 6.6, h: 6.6 * 781 / 1409, objectName: "model d horizon" });
  card(s, M + 6.9, 1.35, 5.25, 1.6, "O que os números sustentam", "Demanda por rota, 1 mês à frente: WAPE 18,7% vs 24,1%. Ocupação: 6,06 vs 6,54 pts.", { fill: "E6F4EF" });
  card(s, M + 6.9, 3.1, 5.25, 2.95, "Limitações declaradas", "", { fill: "F3F6FB" });
  s.addText(bullets(["Módulo D subestima cerca de 12%; em 6 meses perde do baseline",
    "Teste 2024–2025 selado e não executado",
    "Treino sem os 4 meses ausentes",
    "Associações, não causas; sem tarifas na base"], 14),
    { x: M + 7.15, y: 3.7, w: 4.8, h: 2.3, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  caption(s, "Reprodutível: research/ml-showcase/reproduce.py --refit recalcula as métricas e reajusta os modelos em memória.");
}
// ---------- 9. Analyst
{
  const s = pres.addSlide({ masterName: "CONTENT" }); s.addText("AI Analyst e integração com Groq", { placeholder: "title" });
  shot(s, "screenshots/analyst-live-busiest-airports.jpg", M, 1.4, 7.2, undefined, "Analyst respondendo ao vivo");
  s.addText(bullets(["Perguntas em linguagem natural respondidas só por 5 ferramentas fixas e somente leitura",
    "Todo número da resposta é conferido contra o resultado da ferramenta; rascunhos errados são recusados",
    "Fontes, período e unidade anexados pelo código, não pelo modelo",
    "Chave da Groq só no servidor; limite de 10 perguntas/hora por visitante e 200/dia no total"], 14),
    { x: M + 7.45, y: 1.45, w: 4.7, h: 4.6, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  caption(s, "Resposta real em 2026-11-08; os 5 aeroportos e movimentos conferem com /v2/airports. O verificador é heurístico: não garante toda associação.", 5.75);
}
// ---------- 10. Demo & conclusions
{
  const s = pres.addSlide({ masterName: "TITLE_DARK" });
  s.addText("Demonstração pública, tecnologias e conclusões", { x: M, y: 0.45, w: W - 2 * M, h: 0.8, fontSize: 34, bold: true, color: "FFFFFF", margin: 0, isTextBox: true });
  const links = [["Dashboard", LIVE], ["AI Analyst", LIVE + "/dashboard/analyst"], ["ML Studio", LIVE + "/dashboard/ml-studio"], ["API", "anac-flight-intelligence-api-v2.onrender.com/docs"]];
  links.forEach((l, i) => s.addText([{ text: l[0] + "  ", options: { bold: true, color: "FFFFFF" } }, { text: l[1], options: { color: "CADCFC", hyperlink: { url: "https://" + l[1] } } }],
    { x: M, y: 1.45 + i * 0.45, w: 7.4, h: 0.4, fontSize: 14, margin: 0, isTextBox: true }));
  const stack = ["Python 3.12", "Polars", "DuckDB", "Parquet", "LightGBM", "FastAPI", "Docker", "Render", "Next.js 16", "React 19", "TypeScript", "Tailwind 4", "Vercel", "Groq"];
  let x = M, y = 3.5;
  stack.forEach((t) => { const w = 0.22 + t.length * 0.105; if (x + w > 8) { x = M; y += 0.5; }
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 0.38, rectRadius: 0.19, fill: { color: "1F3F7A" }, line: { color: "1F3F7A" } });
    s.addText(t, { x, y, w, h: 0.38, fontSize: 12, color: "FFFFFF", align: "center", valign: "middle", margin: 0, isTextBox: true }); x += w + 0.12; });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.4, y: 1.45, w: W - M - 8.4, h: 3.9, rectRadius: 0.14, fill: { color: "FFFFFF", transparency: 0 }, line: { color: "FFFFFF" } });
  s.addText("Conclusões", { x: 8.7, y: 1.65, w: 3.8, h: 0.4, fontSize: 18, bold: true, color: C.text2, margin: 0, isTextBox: true });
  s.addText(bullets(["Dados abertos viram respostas corretas quando as regras de contagem são explícitas e testadas",
    "ML só onde vence o baseline com confiança; onde não vence, o projeto diz",
    "IA generativa útil quando presa a ferramentas fixas e verificação numérica"], 14),
    { x: 8.7, y: 2.15, w: 3.8, h: 3.1, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  s.addText("Construído com Claude Code e Codex sob regras escritas e aprovação humana de cada etapa.", { x: M, y: 6.6, w: W - 2 * M, h: 0.35, fontSize: 12, color: "CADCFC", margin: 0, isTextBox: true });
}
} else {
// ---------- EN summary: 3 slides after the title
{
  const s = pres.addSlide({ masterName: "CONTENT" }); s.addText("What it is and why it matters", { placeholder: "title" });
  stat(s, M, 1.4, 2.8, "20 GB", "ANAC open data, every Brazilian flight leg since 2000");
  stat(s, M, 2.85, 2.8, "22.1M", "rows ingested and audited, none rejected");
  stat(s, M, 4.3, 2.8, "308", "months with data, 2000-01 to 2025-12 (4 absent)");
  shot(s, "screenshots/dashboard-overview-kpis.jpg", 3.75, 1.45, 8.95, undefined, "Overview");
  s.addText("Pipeline: audited Parquet ingestion → point-in-time features → LightGBM vs baselines → star schema → read-only FastAPI (Render, Docker) → Next.js dashboard (Vercel) → AI analyst (Groq).",
    { x: 3.75, y: 6.0, w: 8.95, h: 0.7, fontSize: 13, color: C.text1, margin: 0, isTextBox: true });
}
{
  const s = pres.addSlide({ masterName: "CONTENT" }); s.addText("Machine learning, honestly evaluated", { placeholder: "title" });
  s.addImage({ path: img("charts/ml-validation-2023-vs-baselines.png"), x: M, y: 1.3, w: 10.2, h: 10.2 * 935 / 2376, objectName: "ml chart" });
  s.addText(bullets(["2023 validation on unseen data; adopted only if it beats the best baseline with a 95% interval excluding zero",
    "Route demand, 1 month ahead: WAPE 18.7% vs 24.1%"], 14),
    { x: M, y: 5.45, w: 5.9, h: 1.0, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  s.addText(bullets(["Airport traffic: no conclusive gain, so the simple rule is kept",
    "Limits: about −12% bias on route demand, worse than baseline at 6 months, 2024–2025 test not run"], 14),
    { x: M + 6.2, y: 5.45, w: 5.9, h: 1.0, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  caption(s, "Labels in the chart are in Portuguese. Source: research/ml-showcase/REPORT.md. Validation results, not forecasts.");
}
{
  const s = pres.addSlide({ masterName: "CONTENT" }); s.addText("AI analyst and live demo", { placeholder: "title" });
  shot(s, "screenshots/analyst-live-busiest-airports.jpg", M, 1.4, 7.2, undefined, "Analyst live");
  s.addText(bullets(["Answers only through 5 fixed, read-only tools; every number is checked against the tool result before it is shown",
    "Sources, period and unit attached by code, not by the model",
    "Groq key server-side only; 10 questions per visitor per hour, 200 per day overall",
    "Live: " + LIVE], 14),
    { x: M + 7.45, y: 1.45, w: 4.7, h: 4.6, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  caption(s, "Real answer on 2026-11-08, matching /v2/airports. The numeric check is heuristic.", 5.75);
}
}
pres.writeFile({ fileName: OUT }).then(async () => { await applyTheme(OUT, THEME); console.log("wrote", OUT); });
