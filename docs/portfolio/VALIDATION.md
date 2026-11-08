# Portfolio validation report

Date: **2026-11-08**. Base: consolidated technical commit `100e509`. Portfolio source: Claude commit `76e210c`, integrated by cherry-pick as `28fc83f` on `codex/portfolio-final`. Primary language: English; corrected Portuguese materials remain secondary.

## Scope and preservation

Only documentation, screenshots, charts and portfolio tooling changed. Application source, tests, configuration, original reports, frozen models and the audited ML payload remain unchanged. The Power BI worktree was not accessed. No Groq call, real-model training, Docker publication or manual Render/Vercel change was performed. GitHub integrations may automatically build previews or production on pushes/merges.

The README no longer recommends a refit as reproduction of the corrected D procedure. It distinguishes selection predictions from final boosters, seat occupancy from RPK/ASK, and validation from forecasting. Six English ML guides reference the original audit; all 90 visual-entry IDs are preserved. Counts remain four regressors, ten baseline references, 26 web charts and 37 report figures.

## Application checks rerun for this integration

| Check | Actual result |
|---|---|
| Full pytest suite | **368 passed, 11 skipped**, one Starlette/httpx deprecation warning |
| Python skips | Raw CSV, real feature panels or serving payload fixtures absent in isolated checkout |
| Ruff lint and format | Passed; 71 source/test/audit-script files formatted |
| Strict mypy | Passed, 48 source files |
| Frontend integration tests | **91 passed, no skips**, with local API at 127.0.0.1:8005 using existing serving/analytics data read-only |
| Frontend ESLint / TypeScript | Passed |
| Next.js production build | Passed: compilation, TypeScript and 12 static pages generated |

The local API had both Groq-key environment variables empty; provider interactions in tests use mocks. Synthetic fitting fixtures in pytest are not retraining of the four production models. Analytical historical queries are not ML holdout evaluation.

## Document and asset validation

**31 document/asset checks passed**, including 132 local link references. Git attributes explicitly preserve PDF/PPTX/image bytes as binary to prevent line-ending conversion.

Machine-readable checks are in [validation.json](validation.json), produced by [validate_portfolio.py](tools/validate_portfolio.py). They cover local Markdown links/anchors, image decoding, PDF/PPTX archive validity, ten slides/pages per language, per-slide text parity, required figures/caveats, text bounds, English compatibility aliases, chart-inventory parity, historical metric rounding, protected-file Git comparison, credential patterns and public GET links. Presentation SHA-256 hashes are recorded.

The ten English PDF slides were rendered and visually inspected. PDF is the fixed-layout reference; PPTX uses editable text/shapes and the same source coordinates/assets. Native PowerPoint rendering was not executed; font substitution on another system remains possible. Arial is embedded in PDF and expected on the presentation machine. Rebuild commands and pinned document dependencies are in [tools/README.md](tools/README.md).

Seven ML Studio screenshots were refreshed from production with chat/status blocked. Existing Analyst captures are historical examples from Claude, not fresh provider runs. Covers are editorial montages. Three English portfolio charts are separate from the 26/37 audited visualization counts. Annual chart values were checked against 308 public monthly analytical points; hatched partial years are explicitly labelled unknown-gap totals.

Credential verification is a pattern scan of the current tracked/candidate snapshot, not all historical commits, a dependency audit or a security certification. It prints only paths/counts, never matched secrets.

## Methodological limits that remain

- A: gain inconclusive; retain baseline.
- D: historical missing-target zero-fill defect; loader corrected, **not retrained**, impact unknown; approximately −12% bias and no established gain at every horizon.
- 2024–2025 holdout: partially exposed, not scored, not fully blind.
- C: not trained. Legacy model results are not reproduced current evidence.
- Historical 2023 validation is not a future forecast; no operational inference endpoint. Month-cluster metric intervals are not predictive bands.
- Verifier is heuristic; rate limiting is per-process memory state. No unmeasured commercial-impact, productivity or universal-generalization claim.

## Publication plan

Review and merge the portfolio PR into `feat/ingestion-v2` after checks pass. Open a separate PR from the consolidated branch into `main` for owner review; **do not merge main**. Existing deployed code needs no functional redeploy for this documentation-only release. No provider availability or production configuration is revalidated by local tests.
