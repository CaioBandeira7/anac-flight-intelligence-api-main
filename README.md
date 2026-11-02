# ANAC Flight Intelligence API

Four machine-learning models behind one API, trained on 20 GB of open data from ANAC, Brazil's civil aviation agency (domestic and international flights, 2018–2024).

Send a route, an airline and a date. Get back airport congestion, expected seat occupancy, price pressure and the probability of excess baggage.

**Live API docs:** [anac-flight-intelligence-api-production.up.railway.app/docs](https://anac-flight-intelligence-api-production.up.railway.app/docs) · **Portfolio:** [caiobandeira7.github.io](https://caiobandeira7.github.io)

## Models

| Prediction | Architecture | Task | Metric |
|---|---|---|---|
| Airport congestion | Bidirectional LSTM with attention | Regression on hourly flow | MAE |
| Seat occupancy | FT-Transformer | Multi-task: occupancy + overbooking | MAE, AUC |
| Price pressure | MLP with categorical embeddings | Regression on a price index | MAE |
| Excess baggage | LightGBM + neural network stack | Binary classification | AUC-ROC |

## Example

```bash
curl -X POST https://anac-flight-intelligence-api-production.up.railway.app/prever \
  -H "Content-Type: application/json" \
  -d '{
    "aeroporto_origem": "GRU",
    "aeroporto_destino": "GIG",
    "empresa": "LATAM",
    "data_voo": "2026-07-15",
    "peso_bagagem_kg": 20.0
  }'
```

```json
{
  "prob_aeroporto_cheio": 0.74,
  "taxa_ocupacao_voo": 0.89,
  "bucket_ocupacao": "lotado",
  "pressao_preco": 0.638,
  "recomendacao_preco": "premium",
  "prob_excesso_bagagem": 0.038,
  "recomendar_cobranca": false,
  "justificativa_bagagem": "Baixo histórico de excesso nesta rota"
}
```

Other endpoints: `GET /health`, `GET /historico` (occupancy history by route), `GET /cache/stats`, `DELETE /cache`.

## Pipeline

| Step | Script | What it does |
|---|---|---|
| 0 | `00_verificar_dados.py` | Checks the raw ANAC files |
| 1 | `01_ingestao.py` | Raw CSV (~20 GB) to Parquet with Polars |
| 2 | `02_feature_engineering.py` | Feature tables for the four models |
| 3 | `03_modelo_aeroporto.py` | Trains the LSTM (congestion) |
| 4 | `04_modelo_assentos.py` | Trains the FT-Transformer (occupancy) |
| 5 | `05_modelos_preco_bagagem.py` | Trains the MLP (pricing) and the LightGBM + NN stack (baggage) |
| 6 | `06_api.py` | FastAPI inference server |
| 7 | `07_monitorar_drift.py` | Monthly drift report for all four models |

Data and trained models (`data/`, `models/`) are not versioned because of their size. Run steps 1–5 to rebuild them.

## Engineering decisions

- **FT-Transformer for tabular data:** chosen for seat occupancy because of the strong interactions between route, carrier and season.
- **Multi-task learning:** occupancy and overbooking share one representation.
- **Class imbalance:** stratified splits and `scale_pos_weight` for excess baggage.
- **Route-aware inference:** historical stats looked up by route and carrier, with a three-level fallback when a route is rare.
- **Demo mode:** if model files are missing at startup, the API switches to a lightweight path and keeps answering. `/health` reports which mode is active.
- **Drift monitoring:** Population Stability Index on inputs plus MAE thresholds on outputs.
- **Reproducibility:** fixed seed (42) in every training script.

## Run locally

```bash
pip install -r requirements.txt

# build data and models (once)
python 01_ingestao.py
python 02_feature_engineering.py
python 03_modelo_aeroporto.py
python 04_modelo_assentos.py
python 05_modelos_preco_bagagem.py

# start the API
uvicorn 06_api:app --reload --port 8000
```

API docs at `http://localhost:8000/docs`. `dashboard.html` is a static analytics dashboard; `docker-compose.yml` serves it next to the API once a `Dockerfile` is in place (see `Dockerfile.bak`).

## Roadmap

- [ ] Restore the Docker image with models pulled from storage at build time
- [ ] Automated tests
- [ ] CI/CD with GitHub Actions
- [ ] Deploy on Azure

## Author

Caio Bandeira, data scientist in Brasília. [Portfolio](https://caiobandeira7.github.io) · [LinkedIn](https://www.linkedin.com/in/caio-bandeira-cv) · [GitHub](https://github.com/CaioBandeira7)

Data: ANAC open data, published under Brazil's access to information law.
