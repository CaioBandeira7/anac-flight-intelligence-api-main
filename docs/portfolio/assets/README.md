# Portfolio assets and provenance

English is the primary presentation language. All application screenshots are real; chart values come from tracked results or public historical aggregates. No synthetic forecast or new Analyst answer was generated for this portfolio revision.

| Asset | Provenance |
|---|---|
| `screenshots/` | 21 screenshots integrated from Claude commit `76e210c`; seven ML Studio images refreshed from the current public deployment on 2026-11-08, using Edge/Playwright, with chat/status requests blocked. Desktop 1375×674; refreshed mobile ML 494×730. |
| `analyst-live-*` screenshots | Historical live answers captured by Claude. These are recorded examples, not evidence of new live availability. Their numeric verification remains heuristic. |
| `cover/cover-github-1280x640-en.jpg` | English editorial composition using real dashboard and historical Analyst screenshots. This is a cover montage, not one application screenshot. Portuguese cover retained. |
| `charts/*-en.png` | Three English figures regenerated from tracked `annual-market.json` and `web/public/ml/showcase.json`. All axes, units and caveats are English. |
| `annual-market.json` | 26 annual aggregates from 308 public monthly points, retrieved 2026-11-08; absent months explicitly recorded. 2025 paid passengers: 131,593,763. No ML holdout scoring. |
| Original Portuguese charts | Preserved secondary figures from Claude; primary international materials use the English figures. |
| `../presentation/` | Current 10-slide English PDF/PPTX and corrected 10-slide Portuguese PDF/PPTX. English summary filenames are compatibility aliases of the full English deck. |

## Evidence and limits

Ingestion: 22,120,241 records, 308 observed months; analytics: three dimensions/four facts. Historical validation: A WAPE 10.10% vs 10.30%, inconclusive; B weighted MAE 6.06 pp vs 6.54 pp; D passengers 22.24% vs 25.31%, seats 22.40% vs 25.73%.

D has not been retrained after its missing-target correction. The holdout was partially exposed but unscored. C is not trained. Historical evaluation is not a future forecast. Consolidated test counts are 368 Python passed/11 skipped and 91 frontend passed.

English ML documentation inventories 26 web charts and 37 report figures; the three new portfolio figures do not change those counts. [Full validation](../VALIDATION.md) · [Generator instructions](../tools/README.md).
