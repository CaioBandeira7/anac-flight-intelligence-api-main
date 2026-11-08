"""Generate English charts and matching editable PPTX/vector PDF decks from tracked evidence."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Pt
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs/portfolio"
ASSETS = BASE / "assets"
PRESENTATION = BASE / "presentation"
NAVY = "102A52"
BLUE = "235FD2"
INK = "172C48"
MUTED = "52637A"
PALE = "EAF1FB"
WHITE = "FFFFFF"
W, H = 960, 540


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def charts():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 12,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    market = read("docs/portfolio/assets/annual-market.json")
    rows = market["years"]
    fig, ax = plt.subplots(figsize=(12, 5.5), dpi=160)
    fig.subplots_adjust(bottom=0.24, top=0.84, left=0.08, right=0.98)
    for row in rows:
        ax.bar(
            row["year"],
            row["paid_passengers"] / 1e6,
            color="#235FD2" if row["observed_months"] == 12 else "#B9CCE9",
            hatch=None if row["observed_months"] == 12 else "///",
            edgecolor="#235FD2",
            width=0.72,
        )
    ax.set_title(
        "Paid passengers in ANAC records · 2000–2025",
        loc="left",
        weight="bold",
        pad=20,
        color="#172C48",
    )
    ax.set_ylabel("Paid passengers (millions of flight-leg counts)")
    ax.set_xticks([2000, 2005, 2010, 2015, 2020, 2025])
    ax.grid(axis="y", alpha=0.15)
    ax.set_axisbelow(True)
    ax.annotate(
        "131.6M in 2025",
        (2025, 131.59),
        xytext=(2017, 141),
        arrowprops={"arrowstyle": "-", "color": "#52637A"},
    )
    ax.set_ylim(0, 155)
    fig.text(
        0.08,
        0.08,
        "Hatched bars contain 11 observed months; missing months are unknown, not zero.\nSource: public /v2/analytics/routes/monthly, retrieved 2026-11-08; tracked annual-market.json.",
        fontsize=10,
        color="#52637A",
    )
    fig.savefig(ASSETS / "charts/annual-paid-passengers-2000-2025-en.png")
    plt.close(fig)
    public = read("web/public/ml/showcase.json")["tasks"]
    fig, axes = plt.subplots(1, 4, figsize=(15, 5.5), dpi=160)
    fig.subplots_adjust(bottom=0.29, top=0.78, wspace=0.45, left=0.055, right=0.985)
    labels = {
        "a": "A · Airport movements",
        "b": "B · Seat occupancy",
        "d_pax": "D · Route passengers",
        "d_seats": "D · Route seats",
    }
    for ax, key in zip(axes, labels, strict=True):
        t = public[key]
        m = t["lightgbm"]["value"] * 100
        b = t["baselines"][t["best_baseline"]]["value"] * 100
        ax.bar([0, 1], [m, b], color=["#235FD2", "#9AA8BB"], width=0.6)
        for i, v in enumerate([m, b]):
            ax.text(i, v + 0.4, f"{v:.2f}", ha="center", weight="bold")
        ax.set_xticks([0, 1], ["LightGBM", "Best\nbaseline"])
        ax.set_ylim(0, max(m, b) * 1.3)
        ax.set_title(labels[key], loc="left", fontsize=12, weight="bold")
        ax.set_ylabel("Weighted MAE (pp)" if key == "b" else "WAPE (%)")
        ax.grid(axis="y", alpha=0.15)
        ax.set_axisbelow(True)
        d = t["difference_vs_best_baseline"]
        lo, hi = [v * 100 for v in d["ci95"]]
        ax.text(
            0.5,
            -0.22,
            f"Difference 95% CI:\n[{lo:+.2f}, {hi:+.2f}]\n"
            + ("Inconclusive; keep baseline" if key == "a" else "Historical pooled improvement"),
            transform=ax.transAxes,
            ha="center",
            va="top",
            fontsize=9.5,
            color="#52637A",
        )
    fig.suptitle(
        "2023 selection-model validation · lower error is better",
        x=0.055,
        ha="left",
        fontsize=17,
        weight="bold",
        color="#172C48",
    )
    fig.text(
        0.055,
        0.035,
        "Source: reports/models and audited showcase.json. D has NOT been retrained after its loader fix.\nThe 2024–2025 holdout was partially exposed but unscored. These are validation errors, not future forecasts.",
        fontsize=10,
        color="#52637A",
    )
    fig.savefig(ASSETS / "charts/ml-validation-2023-vs-baselines-en.png")
    plt.close(fig)
    rows = public["d_pax"]["by_horizon"]
    h = [r["horizon"] for r in rows]
    m = [r["model"] * 100 for r in rows]
    b = [min(r["baselines"].values()) * 100 for r in rows]
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=160)
    fig.subplots_adjust(bottom=0.27, top=0.85, left=0.085, right=0.97)
    ax.plot(h, m, "o-", color="#235FD2", label="LightGBM", lw=2.3)
    ax.plot(h, b, "o--", color="#8C9BB0", label="Best baseline at each horizon", lw=2.3)
    for x, y, z in zip(h, m, b, strict=True):
        ax.annotate(
            f"{y:.2f}%",
            (x, y),
            xytext=(0, 12 if y > z else -20),
            textcoords="offset points",
            ha="center",
            color="#235FD2",
            weight="bold",
        )
        ax.annotate(
            f"{z:.2f}%",
            (x, z),
            xytext=(0, -20 if y > z else 12),
            textcoords="offset points",
            ha="center",
            color="#52637A",
        )
    ax.set_xticks(h, [f"{x} month" + ("" if x == 1 else "s") for x in h])
    ax.set_ylim(14, 30)
    ax.set_xlim(0.5, 6.5)
    ax.set_ylabel("WAPE (%)")
    ax.legend(frameon=False)
    ax.grid(alpha=0.15)
    ax.set_title(
        "D · Route passengers: error by horizon, validation 2023", loc="left", weight="bold", pad=15
    )
    fig.text(
        0.085,
        0.075,
        "Source: audited showcase.json, tasks.d_pax.by_horizon. At 6 months the point estimate is worse;\nthe paired interval includes zero. Historical v1 only; no retraining after the missing-target correction.",
        fontsize=10,
        color="#52637A",
    )
    fig.savefig(ASSETS / "charts/ml-model-d-error-by-horizon-en.png")
    plt.close(fig)


class Deck:
    def __init__(self, name, language):
        self.name = name
        self.language = language
        self.pres = Presentation()
        self.pres.slide_width = Pt(W)
        self.pres.slide_height = Pt(H)
        self.pres.core_properties.title = "ANAC Flight Intelligence — " + (
            "English presentation" if language == "en" else "Apresentação em português"
        )
        self.pres.core_properties.author = "Caio Bandeira"
        self.pdf = canvas.Canvas(str(PRESENTATION / (name + ".pdf")), pagesize=(W, H), invariant=1)
        self.pdf.setTitle(self.pres.core_properties.title)
        self.pdf.setAuthor("Caio Bandeira")
        self.number = 0
        self.layout = []

    def rect(self, x, y, w, h, color):
        shape = self.slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Pt(x), Pt(y), Pt(w), Pt(h))
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor.from_string(color)
        shape.line.fill.background()
        self.pdf.setFillColor("#" + color)
        self.pdf.rect(x, H - y - h, w, h, fill=1, stroke=0)

    def text(self, text, x, y, w, h, size=17, color=INK, bold=False):
        font = "PortfolioBold" if bold else "Portfolio"
        lines = []
        for paragraph in text.split("\n"):
            line = ""
            for word in paragraph.split():
                candidate = (line + " " + word).strip()
                if pdfmetrics.stringWidth(candidate, font, size) > w and line:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            lines.append(line)
        step = size * 1.25
        assert len(lines) * step <= h + 0.1, (self.number, text, len(lines) * step, h)
        for i, line in enumerate(lines):
            box = self.slide.shapes.add_textbox(Pt(x), Pt(y + i * step), Pt(w), Pt(step + 3))
            tf = box.text_frame
            tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
            p = tf.paragraphs[0]
            p.text = line
            p.font.name = "Arial"
            p.font.size = Pt(size)
            p.font.bold = bold
            p.font.color.rgb = RGBColor.from_string(color)
            p.space_after = Pt(0)
            self.pdf.setFillColor("#" + color)
            self.pdf.setFont(font, size)
            self.pdf.drawString(x, H - y - i * step - size * 0.97, line)
            target = (
                (
                    "https://github.com/CaioBandeira7/anac-flight-intelligence-api-main"
                    if "github.com/" in line
                    else "https://anac-flight-intelligence-api-main.vercel.app"
                )
                if ("github.com/" in line or "anac-flight-intelligence-api-main.vercel.app" in line)
                else None
            )
            if target:
                p.runs[0].hyperlink.address = target
                self.pdf.linkURL(
                    target, (x, H - y - i * step - step, x + w, H - y - i * step), relative=0
                )
        self.layout.append(
            {
                "slide": self.number,
                "text": text,
                "x": x,
                "y": y,
                "width": w,
                "height": h,
                "font_size": size,
            }
        )

    def image(self, path, x, y, w, h):
        p = ASSETS / path
        with Image.open(p) as im:
            iw, ih = im.size
        scale = min(w / iw, h / ih)
        dw, dh = iw * scale, ih * scale
        x += (w - dw) / 2
        y += (h - dh) / 2
        self.slide.shapes.add_picture(str(p), Pt(x), Pt(y), width=Pt(dw), height=Pt(dh))
        self.pdf.drawImage(str(p), x, H - y - dh, width=dw, height=dh)

    def new(self, title, kicker, source, dark=False):
        self.slide = self.pres.slides.add_slide(self.pres.slide_layouts[6])
        self.number += 1
        self.rect(0, 0, W, H, NAVY if dark else WHITE)
        fg = WHITE if dark else INK
        self.text(kicker.upper(), 42, 28, 870, 20, 10, "A6C5FF" if dark else BLUE, True)
        self.text(title, 42, 64, 876, 85, 30, fg, True)
        self.rect(42, 497, 876, 1, "38537A" if dark else "DCE5F0")
        self.text(source, 42, 508, 820, 18, 8.5, "C6D8F2" if dark else MUTED)
        self.text(f"{self.number:02d}", 886, 506, 32, 22, 11, "C6D8F2" if dark else MUTED)
        self.slide.notes_slide.notes_text_frame.text = source

    def bullet(self, title, body, x, y, w):
        self.text(title, x, y, w, 36, 18, BLUE, True)
        self.text(body, x, y + 39, w, 94, 16, MUTED)

    def end(self):
        self.pdf.showPage()

    def save(self):
        assert self.number == 10
        self.pdf.save()
        self.pres.save(PRESENTATION / (self.name + ".pptx"))
        (PRESENTATION / (self.name + "-layout.json")).write_text(
            json.dumps(self.layout, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )


def deck(language):
    en = language == "en"

    def t(a, b):
        return a if en else b

    name = (
        "anac-flight-intelligence-presentation-en"
        if en
        else "anac-flight-intelligence-apresentacao"
    )
    d = Deck(name, language)
    d.new(
        "ANAC Flight Intelligence",
        t(
            "Brazilian aviation · data, ML and generative AI",
            "Aviação brasileira · dados, ML e IA generativa",
        ),
        "Caio Bandeira · github.com/CaioBandeira7/anac-flight-intelligence-api-main",
        True,
    )
    d.text(
        t(
            "22,120,241 records.\nTraceable analysis.\nHonest model evaluation.",
            "22.120.241 registros.\nAnálise verificável.\nAvaliação honesta de modelos.",
        ),
        42,
        169,
        440,
        145,
        27,
        WHITE,
        True,
    )
    d.text(
        t(
            "Audited ingestion, an analytical dashboard and a tool-grounded AI analyst.",
            "Ingestão auditada, dashboard analítico e um AI Analyst com ferramentas fixas.",
        ),
        42,
        330,
        430,
        100,
        18,
        "C6D8F2",
    )
    d.image("screenshots/dashboard-overview-kpis.jpg", 520, 174, 398, 232)
    d.text("anac-flight-intelligence-api-main.vercel.app", 42, 454, 860, 26, 14, "C6D8F2")
    d.end()
    d.new(
        t("Correct numbers need explicit rules", "Números corretos exigem regras explícitas"),
        t("01 / problem", "01 / problema"),
        "Sources: docs/ingestion.md · docs/analytics.md",
    )
    d.bullet(
        t("Different counts", "Contagens diferentes"),
        t(
            "Flights, passenger flights and airport movements are not interchangeable.",
            "Voos, voos de passageiros e movimentos aeroportuários não são equivalentes.",
        ),
        42,
        160,
        405,
    )
    d.bullet(
        t("Directed routes", "Rotas direcionadas"),
        t(
            "CGH → SDU and SDU → CGH are separate markets. Passengers count per leg.",
            "CGH → SDU e SDU → CGH são mercados separados. Passageiros são contados por etapa.",
        ),
        508,
        160,
        405,
    )
    d.bullet(
        t("Different ratios", "Razões diferentes"),
        t(
            "Seat Occupancy = paid passengers / seats. Passenger Load Factor = RPK / ASK.",
            "Ocupação de assentos = passageiros pagos / assentos. Load Factor = RPK / ASK.",
        ),
        42,
        325,
        405,
    )
    d.bullet(
        t("Unknown is not zero", "Ausente não é zero"),
        t(
            "Four globally absent months remain gaps. Partial annual totals need explicit labels.",
            "Quatro meses globalmente ausentes são lacunas. Totais anuais parciais exigem aviso.",
        ),
        508,
        325,
        405,
    )
    d.end()
    d.new(
        t("An audited data foundation", "Uma base de dados auditada"),
        t("02 / data engineering", "02 / engenharia de dados"),
        "Sources: reports/ingestion/quality_report.json · reports/analytics/validation.json",
    )
    for x, big, label in [
        (42, "22,120,241" if en else "22.120.241", t("records processed", "registros processados")),
        (
            354,
            "308",
            t("observed months / 312 calendar months", "meses observados / 312 no calendário"),
        ),
        (666, "7", t("analytics tables: 3 dimensions + 4 facts", "tabelas: 3 dimensões + 4 fatos")),
    ]:
        d.text(big, x, 160, 280, 60, 31, BLUE, True)
        d.text(label, x, 224, 280, 64, 16, MUTED)
    d.rect(42, 317, 876, 132, PALE)
    d.text(
        t(
            "Bounded chunks → validation flags → atomic Parquet publication → independent DuckDB read-back.",
            "Blocos limitados → flags de validação → publicação atômica em Parquet → releitura independente com DuckDB.",
        ),
        62,
        337,
        832,
        64,
        19,
        INK,
    )
    d.text(
        t(
            "Historical full-run evidence, not a new 20 GB rebuild for this presentation.",
            "Evidência da execução histórica; sem reprocessar 20 GB para esta apresentação.",
        ),
        62,
        410,
        832,
        29,
        13,
        MUTED,
    )
    d.end()
    d.new(
        t("One source, separate analytical paths", "Uma fonte, caminhos analíticos separados"),
        t("03 / architecture", "03 / arquitetura"),
        "Sources: docs/ml/en/ML_ARCHITECTURE.md · src/anac/ · web/",
    )
    stages = [
        ("ANAC CSV", "~20 GB"),
        ("Parquet", t("Audited flights", "Voos auditados")),
        ("Analytics", t("Star schema", "Esquema estrela")),
        ("FastAPI", "Docker / Render"),
        ("Next.js", "Vercel"),
    ]
    for i, (title, body) in enumerate(stages):
        x = 42 + i * 178
        d.rect(x, 161, 164, 87, PALE)
        d.text(title, x + 12, 178, 140, 29, 17, BLUE, True)
        d.text(body, x + 12, 212, 140, 26, 13, MUTED)
    d.bullet(
        "ML",
        t(
            "Point-in-time features → LightGBM / baselines → saved 2023 validation → static ML Studio.",
            "Features point-in-time → LightGBM / baselines → validação salva de 2023 → ML Studio estático.",
        ),
        42,
        291,
        405,
    )
    d.bullet(
        "GenAI",
        t(
            "Five fixed tools → Groq → heuristic numeric verification → sourced answer. No unrestricted SQL.",
            "Cinco ferramentas fixas → Groq → verificação numérica heurística → resposta com fontes. Sem SQL livre.",
        ),
        508,
        291,
        405,
    )
    d.text(
        t(
            "The API does not serve operational future predictions.",
            "A API não serve previsões futuras operacionais.",
        ),
        42,
        455,
        876,
        28,
        16,
        INK,
        True,
    )
    d.end()
    d.new(
        t("A dashboard built around definitions", "Um dashboard com definições explícitas"),
        t("04 / product", "04 / produto"),
        "Real public screenshots, refreshed ML views 2026-11-08. Figures are historical, not live forecasts.",
    )
    d.image("screenshots/dashboard-overview-kpis.jpg", 42, 151, 425, 245)
    d.image("screenshots/routes-explorer-ranking.jpg", 493, 151, 425, 245)
    d.text(
        t(
            "Market, airports, directed routes and airlines. Period filters, API/DEMO labels, loading/error states and missing-month warnings.",
            "Mercado, aeroportos, rotas direcionadas e empresas. Filtros, rótulos API/DEMO, estados de erro e avisos de meses ausentes.",
        ),
        42,
        421,
        876,
        66,
        18,
        INK,
    )
    d.end()
    d.new(
        t("Temporal evaluation, not future forecasts", "Avaliação temporal, não previsão futura"),
        t("05 / experiment protocol", "05 / protocolo experimental"),
        "Sources: configs/models.toml · src/anac/models/train.py · audit.json",
    )
    for x, title, body in [
        (
            42,
            t("FIT / EARLY STOP", "TREINO / EARLY STOP"),
            t(
                "Purged 2013–2021 fitting; 2022 early stopping. Two-month publication lag.",
                "Treino 2013–2021 com purge; early stopping em 2022. Defasagem de publicação de dois meses.",
            ),
        ),
        (
            493,
            t("VALIDATE / FREEZE", "VALIDAR / CONGELAR"),
            t(
                "Saved selection predictions evaluated on 2023. Final refit boosters include eligible 2023 history.",
                "Predições de seleção avaliadas em 2023. Boosters finais incluem histórico elegível de 2023.",
            ),
        ),
    ]:
        d.bullet(title, body, x, 160, 425)
    d.rect(42, 326, 876, 118, PALE)
    d.text(
        t(
            "2024–2025 holdout: partially exposed through earlier annual-total inspection; NOT scored. It is not fully blind.",
            "Holdout 2024–2025: parcialmente exposto por inspeção prévia de totais anuais; NÃO pontuado. Não é totalmente cego.",
        ),
        62,
        346,
        832,
        84,
        20,
        INK,
        True,
    )
    d.text(
        t(
            "12 target-month clusters · 2,000 bootstrap draws · intervals describe metric uncertainty.",
            "12 clusters mensais · 2.000 amostragens bootstrap · intervalos de incerteza da métrica.",
        ),
        42,
        459,
        876,
        29,
        13,
        MUTED,
    )
    d.end()
    d.new(
        t(
            "Four regressors, ten baseline references",
            "Quatro regressores, dez referências baseline",
        ),
        t("06 / verified 2023 results", "06 / resultados verificados de 2023"),
        "Source: reports/models/module_{a,b,d}.json · errors rounded to two decimals; pp = percentage points.",
    )
    headers = [
        t("Experiment", "Experimento"),
        "LightGBM",
        t("Best baseline", "Melhor baseline"),
        t("Historical verdict", "Conclusão histórica"),
    ]
    widths = [270, 140, 150, 316]
    x = 42
    for h, w in zip(headers, widths, strict=True):
        d.rect(x, 157, w, 39, NAVY)
        d.text(h, x + 10, 168, w - 20, 23, 13, WHITE, True)
        x += w
    rows = [
        (
            "A · " + t("Airport movements", "Movimentos"),
            "10.10%",
            "10.30%",
            t("Inconclusive; baseline kept", "Inconclusivo; manter baseline"),
        ),
        (
            "B · " + t("Seat occupancy", "Ocupação"),
            "6.06 pp",
            "6.54 pp",
            t("Pooled CI favors model", "IC agregado favorece modelo"),
        ),
        (
            "D · " + t("Passengers", "Passageiros"),
            "22.24%",
            "25.31%",
            t("Historical result; see caveat", "Resultado histórico; ver ressalva"),
        ),
        (
            "D · " + t("Seats", "Assentos"),
            "22.40%",
            "25.73%",
            t("Historical result; see caveat", "Resultado histórico; ver ressalva"),
        ),
    ]
    for i, row in enumerate(rows):
        x = 42
        for text, w in zip(row, widths, strict=True):
            d.rect(x, 196 + i * 49, w, 49, PALE if i % 2 == 0 else "F5F8FC")
            d.text(text, x + 10, 211 + i * 49, w - 20, 35, 14, INK)
            x += w
    d.text(
        t(
            "A: difference 95% CI includes zero. WAPE ≠ accuracy.\nB: actual-seat-weighted MAE, not RPK/ASK error. C is NOT trained.",
            "A: IC 95% da diferença inclui zero. WAPE não é accuracy.\nB: MAE ponderado por assentos, não erro de RPK/ASK. C NÃO foi treinado.",
        ),
        42,
        421,
        876,
        65,
        17,
        INK,
    )
    d.end()
    d.new(
        t("The route-model caveat stays visible", "A ressalva do modelo de rotas é explícita"),
        t("07 / audit findings", "07 / achados da auditoria"),
        "Sources: audit.json · docs/ml/en/EXPERIMENT_RESULTS.md. D historical scores are not corrected-model evidence.",
    )
    d.rect(42, 155, 876, 104, PALE)
    d.text(
        t(
            "Historical D training filled globally absent target months with zero. The loader is corrected; frozen v1 models have NOT been retrained.",
            "O treino histórico de D preencheu meses globalmente ausentes com zero. O loader foi corrigido; os modelos v1 NÃO foram retreinados.",
        ),
        62,
        175,
        832,
        78,
        21,
        INK,
        True,
    )
    d.bullet(
        t("Impact not measured", "Impacto não medido"),
        t(
            "11,689 passenger and 11,692 seat fitting rows were affected. No causal performance improvement can be claimed.",
            "11.689 linhas de passageiros e 11.692 de assentos afetadas no fitting. Não há melhora causal de performance comprovada.",
        ),
        42,
        295,
        405,
    )
    d.bullet(
        t("Horizon and bias limits", "Limites de horizonte e viés"),
        t(
            "About −12% aggregate bias. Six-month point errors are worse; paired intervals include zero.",
            "Viés agregado de cerca de −12%. Pontos de erro a seis meses são piores; ICs pareados incluem zero.",
        ),
        508,
        295,
        405,
    )
    d.text(
        t(
            "Corrected AP handles ties. Occupancy bias now uses seat weights and explicit units.",
            "AP corrigida trata empates. Viés de ocupação usa pesos de assentos e unidade explícita.",
        ),
        42,
        457,
        876,
        29,
        14,
        MUTED,
    )
    d.end()
    d.new(
        t(
            "Generative AI with controlled data access",
            "IA generativa com acesso controlado aos dados",
        ),
        t("08 / ai analyst", "08 / ai analyst"),
        "Source: historical live screenshot; src/anac/agent/ and src/anac/api/ratelimit.py. No new Groq call for this deck.",
    )
    d.image("screenshots/analyst-live-busiest-airports.jpg", 42, 154, 480, 281)
    d.text(
        t(
            "Five fixed read-only tools.\nSources attached by code.\nNumeric membership checks; not guaranteed semantic attribution.\nQuotas: 10/client/hour, 200/day by default, per-process memory.",
            "Cinco ferramentas fixas e somente leitura.\nFontes anexadas pelo código.\nVerificação numérica não garante atribuição semântica.\nLimites padrão: 10/cliente/hora, 200/dia, memória por processo.",
        ),
        548,
        161,
        370,
        282,
        18,
        INK,
    )
    d.text(
        t(
            "Server-side key · one corrective attempt before refusal · no fare data.",
            "Chave no servidor · uma tentativa de correção antes da recusa · sem tarifas.",
        ),
        42,
        459,
        876,
        28,
        14,
        MUTED,
    )
    d.end()
    d.new(
        t("Verifiable delivery, ready to discuss", "Entrega verificável, pronta para avaliação"),
        t("09 / quality, ownership and demo", "09 / qualidade, autoria e demonstração"),
        "Sources: docs/portfolio/VALIDATION.md · docs/ml/INTEGRATION.md",
        True,
    )
    d.text(
        t(
            "368 Python passed · 11 skipped\n91 frontend passed\n601 ML reconciliation checks",
            "368 Python aprovados · 11 ignorados\n91 frontend aprovados\n601 verificações de reconciliação ML",
        ),
        42,
        157,
        876,
        116,
        27,
        WHITE,
        True,
    )
    d.text(
        t(
            "Lint, types and production build passed. Skips require absent local data.\nDirected by Caio Bandeira; AI-assisted implementation with Claude Code and Codex. No measured commercial-impact claim.",
            "Lint, tipos e build aprovados. Skips exigem dados locais ausentes.\nDireção de Caio Bandeira; implementação assistida por Claude Code e Codex. Sem alegação de impacto comercial medido.",
        ),
        42,
        293,
        860,
        104,
        18,
        "C6D8F2",
    )
    d.text(
        "Live: anac-flight-intelligence-api-main.vercel.app\nGitHub: github.com/CaioBandeira7/anac-flight-intelligence-api-main",
        42,
        424,
        876,
        55,
        14,
        "C6D8F2",
    )
    d.end()
    d.save()


def main():
    fonts = Path(
        os.environ.get(
            "PORTFOLIO_FONT_DIR", str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts")
        )
    )
    for name, file in [("Portfolio", "arial.ttf"), ("PortfolioBold", "arialbd.ttf")]:
        pdfmetrics.registerFont(TTFont(name, str(fonts / file)))
    PRESENTATION.mkdir(parents=True, exist_ok=True)
    charts()
    deck("en")
    deck("pt")
    for ext in ["pdf", "pptx"]:
        shutil.copyfile(
            PRESENTATION / f"anac-flight-intelligence-presentation-en.{ext}",
            PRESENTATION / f"anac-flight-intelligence-summary-en.{ext}",
        )
    print("English charts and two 10-slide decks generated from tracked evidence.")


if __name__ == "__main__":
    main()
