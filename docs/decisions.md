# Decision log

Modelling decisions and data versions, in order. Append, do not rewrite.

## Data versions

| Name | Content | Status on 2026-11-06 |
|---|---|---|
| `anac_brazil.csv` | Kaggle snapshot, SHA-256 `69709a17376b74cea029a5730f07f2b9130aa31798b9d5b8a61d204cb81a91ab` | Never modified |
| `flights` | 22,120,241 legs in 308 months, built from the CSV | Published. Used by features v1 |
| `flights_v2_1` | `flights` plus four months from official ZIPs | Waiting for the ZIPs |
| `flights_eval_2026` | 2026-01 to 2026-09 from official ZIPs, kept apart | Waiting for the ZIPs |
| `Dados_Estatisticos.csv` | ANAC aggregate, last modified 2026-11-06 | Reference only |
| Features v1 | `data/features/v1`, dataset digest and config fingerprint in each manifest | Built from `flights`, up to 2023-12 |

## Decisions

1. **Temporal evaluation.** Train on targets from 2013 up to the purge limit, validate on 2023, test on 2024-2025 with no selection or tuning. `first_target` can move to 2003-01 for the long-window experiment, adopted only if validation error falls with an interval excluding zero at every horizon.
2. **Later evaluation.** 2026-01 to 2026-09, if the official files are available and compatible. These data have been observed, so it is not called prospective in the strict sense. Its results are never used for further optimisation.
3. **Test exposure.** Annual totals for 2024-2025, and baggage series up to 2025, were seen during the audit. They were not used to choose features for A, B or D. The test period is not fully blind, and any report must say so.
4. **Publication lag.** Assumed to be 2 months, because 2026-09 was the latest month published on 2026-11-06. To be tested at 3.
5. **Revisions.** Backtests use revised data, since no historical vintages exist in this dataset. This may flatter the most recent months.
6. **Module C target.** Excess baggage was rejected: it measures who reports. Total checked baggage per paid passenger replaces it provisionally.
7. **Gol, 2019-05 to 2021-08.** Treated as a change in recording, not behaviour. Gol alone drops from about 7 to 3 kg per passenger within two months, up to 18% of its flights report zero during the transition, and it jumps back from 4.8 to 8 in 2021-09. Azul and TAM show nothing similar, and Gol's month-to-month route ranking stays at 0.84 to 0.88. Details in [gol_investigation.json](../reports/baggage/gol_investigation.json). ANAC's documentation was not available to confirm the cause.
8. **Module C gate.** Criteria were fixed in `scripts/assess_module_c.py` before running it, using data up to 2022. Result: AZU, TAM and PTB qualify, covering 61.5% of domestic paid passengers against a 60% minimum, so the margin is small. Gol fails with 31 admitted months against 36, even though its route persistence outside the block is 0.88. The module may proceed to a baseline, and is suspended if a model does not beat it on validation.
9. **Correction to the gate's method.** The first run returned "suspend", because the market reference included Gol and its step made TAM and PTB look shifted. A second version oscillated between passes and silently admitted Gol in 2019-09 to 2019-12. The final version compares carriers in pairs and requires a majority. Thresholds did not change, but the method was changed after seeing a result, so this verdict deserves less weight than one from a method fixed in advance.
10. **Load factor above 1.** Flights above 1.5 are recording errors for B and D. Between 1 and 1.5 they are kept, and aggregates may rarely exceed 1.
11. **No fares.** The dataset has no ticket prices. Module D predicts passengers carried and seats, which is demand served, not unconstrained demand.
12. **Model configuration.** One conservative LightGBM configuration, fixed before seeing validation, with early stopping on 2022 targets rather than on 2023. Frozen in `models/v1`, built from `flights`. The test period was not read.
13. **Module A.** The LightGBM model did not beat the recent-weekday baseline on validation (difference -0.21 points, interval -0.84 to 0.35). Reported as such, not retuned.
14. **AI Aviation Analyst validation.** Run against Groq with `openai/gpt-oss-120b`; reports are in `reports/agent/`. Cases 1 and 4 passed after fixes. In case 6, the answer's content was validated on Groq, but its status was fixed afterwards and validated offline with the recorded tool sequence, by decision of the project owner. Answers do not always follow the question's language, which is left for a later stage.


## Corrective ML audit on the isolated codex/ml-audit-ifood branch

- Preserve frozen v1 and its reported 2023 scores. Use saved selection predictions for
  reconciliation; final boosters were refit using eligible 2023 labels and cannot rescore it.
- Exclude globally missing target months before filling known route inactivity as zero.
  v1 D fitting included 11,689 pax and 11,692 seats rows with unknown targets. Corrected real
  training requires a new version and was not run. Its performance impact is not measured.
- Baseline/model evaluation must reject sealed features and targets, regardless of split labels;
  the daily guard follows TimeConfig instead of a hardcoded calendar year.
- Average precision groups tied scores by threshold. Its old order dependence affected the
  baseline slightly; WAPE/weighted MAE and the LightGBM artifacts are unchanged.
- Display B signed error with actual-seat weights in percentage points, preserving the historical
  relative bias field. Label residual population, clipping, sampled scatter and pooled examples.
- Publish the new audit documentation and errata only on this branch; no merge, push, deploy,
  model retraining or 2024–2025 scoring is part of this audit.
