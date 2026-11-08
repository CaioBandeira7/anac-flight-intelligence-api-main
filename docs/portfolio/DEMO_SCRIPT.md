# Demo video script (75–90 s)

**Setup before recording:**
- Start the API and the dashboard (README, "Run locally"), and use the DAY theme, 1440 × 900.
- The analyst segment shows **recorded** runs, so no model is called while recording.
- To show a live question as well, set `GROQ_API_KEY` first and note that it calls the provider.

Each frame below has a matching real screenshot in `docs/portfolio/screenshots/`.

| # | Time | Screen | Action | Voice-over |
|---|---|---|---|---|
| 1 | 0–10 s | Landing page, then the boarding pass | Click to board | "Brazil's aviation agency publishes every flight since 2000 — 20 gigabytes nobody can read directly. This turns it into answers." |
| 2 | 10–25 s | `/dashboard` (`overview-day.png`) | Open the period picker, choose "Last 6 months" | "131.6 million paid passengers in 2025, compared with the same months a year earlier. Every number says its period and unit; missing months are flagged, never shown as zero." |
| 3 | 25–35 s | `/dashboard/routes` (`routes-day.png`) | Type "congonhas" in Origin, then "santos dumont", then Swap | "Routes have a direction: Congonhas to Santos Dumont is not the same as the way back." |
| 4 | 35–52 s | `/dashboard/analyst#in-action` (`analyst-in-action-day.png`) | Show Market analysis, scroll to the rejected draft, then the verification table | "The AI analyst answers through fixed tools. Here the verifier blocked a draft that attached a number to the wrong metric — and the final answer matches the data, checked independently." |
| 5 | 52–68 s | `/dashboard/ml-studio` (`ml-studio-day.png`) | Show A, then D · Route passengers, 6 mo ahead | "Three forecasting problems, tested on 2023 data the models never saw. For airport traffic, machine learning didn't beat a simple weekday rule — so we keep the rule. For route demand it helps a month ahead, but under-forecasts by 12%." |
| 6 | 68–80 s | `docs/portfolio/CASE_STUDY.md`, or the repository tree | Scroll past `AGENTS.md` and the worktree table | "Built with Claude Code and Codex working under shared rules, in separate directories and worktrees, with every stage and commit approved by a human." |
| 7 | 80–88 s | Report PDF cover | — | "Everything is reproducible, and the limits are written down. Thanks for watching." |

## Storyboard checklist

- [ ] No real secrets visible (do not show `.env`).
- [ ] The analyst is labelled **recorded**, not live, unless a live question is actually asked.
- [ ] Say "validation 2023" whenever a model metric is on screen.
- [ ] Do not mention a public URL until one exists.
