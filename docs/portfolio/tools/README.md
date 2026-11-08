# Rebuild and validate portfolio materials

These tools use tracked aggregate evidence and screenshots. They do not train models, rebuild data or call the LLM. Application dependencies remain unchanged.

## Environment

Use Python 3.12. From the repository root:

```powershell
.venv\Scripts\python -m pip install -r docs/portfolio/tools/requirements.txt
.venv\Scripts\python docs/portfolio/tools/english_ml.py
.venv\Scripts\python docs/portfolio/tools/build_portfolio.py
.venv\Scripts\python docs/portfolio/tools/validate_portfolio.py
```

The deck generator uses Arial regular/bold from `C:/Windows/Fonts` by default. On another OS, set `PORTFOLIO_FONT_DIR` to a directory containing `arial.ttf` and `arialbd.ttf` (fonts must be supplied under their applicable licence). PDF embeds fonts; PowerPoint text stays editable and uses Arial. The PDF is the fixed-layout reference. Dependency versions are pinned in this folder; they are separate from backend production dependencies.

## Sources and outputs

- `english_ml.py`: six English guides and a 90-entry English inventory, from the original tracked audit, inventory and public validation payload. The original Portuguese audit remains untouched.
- `build_portfolio.py`: three English charts, ten-slide English and Portuguese PDF/PPTX decks and layout JSON. English `summary-en` names are compatibility copies of the full deck. Editable PPTX and vector PDF use the same text coordinates, line wrapping and images.
- `validate_portfolio.py`: local document/image links, metric parity, 10-slide PDF/PPTX checks, text parity, required caveats, image integrity, credential-pattern scan, source hashes and public GET links. Creates `docs/portfolio/validation.json`.
- Inputs: `assets/annual-market.json` (dated public analytical aggregates), `web/public/ml/showcase.json`, `research/ml-showcase/results/audit.json`, original chart inventory and screenshots. No raw flight records, frozen models or holdout labels are needed for these document generators.

The older `charts.py`, `cover.py` and `process_shots.py` preserve Claude's original asset-generation provenance and platform-specific paths; they are archival, not the maintained rebuild entry point. `deck.js` forwards to the maintained Python generator and no longer depends on a private skill file. Existing editorial cover assets are reused rather than redesigned.

## Screenshot policy

Use a fresh browser context and the public application, wait for real API data and completed animations, and record capture date/viewport. Never populate a chart with simulated forecasts. The seven refreshed ML screenshots were taken at desktop 1375×674 or mobile 494×730; chat/status routes were blocked. The Analyst images are historical live captures supplied by Claude; this task made no provider calls. The cover is labelled as an editorial montage.

## Full application checks

```powershell
.venv\Scripts\python -m pytest -q
.venv\Scripts\ruff check src tests
.venv\Scripts\ruff format --check src tests
.venv\Scripts\mypy src
cd web
npm.cmd run typecheck
npm.cmd run lint
# ANAC_API_URL may point to a local API to include the seven optional tests.
npm.cmd run test
npm.cmd run build
```

See [validation](../VALIDATION.md) for actual counts, skips and limitations. Do not infer that all optional tests passed from an execution without `ANAC_API_URL`.
