# DynamiX Experiment Runbook — Bundle README

This bundle turns the three experiment groups from the review log
("Bài chỗ anh Tú") into a **runnable experiment plan** plus **validated
analysis/plotting code** that produces the paper's Section V figures the
moment real cluster logs land.

Everything here is validated end-to-end against **synthetic placeholder
data** (42 runs). When real runs arrive, drop their CSVs into `data/`
(same schema) and re-run the two scripts — no code changes needed.

> ⚠️ **The numbers in `tables/*.csv` and `figures/F*.png` are from
> `make_synthetic_runs.py`, not from the cluster.** They exist only to
> prove the pipeline works and to show the intended figure layout. Delete
> `data/` and repopulate with real runs before quoting any result.

---

## What's in the bundle

### Plan & contract (read these first)
| file | what it is |
|---|---|
| `runbook.md` | The experiment plan: prerequisites §0, Group 1/2/3 procedures, master run matrix (39 new runs, ~29 h), review-log mapping. |
| `metrics_schema.md` | Human-readable data contract — every column, the `weight_scale` definition, Prometheus/kubectl collection commands, validation rules. |
| `metrics_schema.json` | Machine-readable version of the same contract; `dynamix_analysis.py` validates every loaded CSV against it. |

### Code
| file | what it does |
|---|---|
| `dynamix_analysis.py` | Loads + schema-validates all runs, derives per-level metrics (throughput, p95/p99 latency, settling time, CoV, rebalance counts, saturation gap), writes `tables/group{1,2,3}_summary.csv`. |
| `dynamix_plots.py` | Renders F1–F6 (see below) from the loaded runs. Publication style via `figstyle.py`. |
| `make_synthetic_runs.py` | **Placeholder data generator.** Fabricates plausible runs so the pipeline can be tested before the cluster is ready. Not part of the real workflow. |
| `figstyle.py` | Figure-style helper (`apply_figure_style()`, `panel_letter()`) for consistent publication-grade output. |

### Outputs (currently synthetic)
- `data/` — `run_metadata.csv` + per-run `timeseries_*.csv` / `rebalance_*.csv`
- `tables/` — three group summary CSVs
- `figures/` — F1–F6 PNGs

---

## Quickstart

```bash
cd runbook

# 1. (only for a dry run) regenerate synthetic data
python3 make_synthetic_runs.py data

# 2. validate + summarise -> tables/
python3 dynamix_analysis.py data metrics_schema.json

# 3. render figures -> figures/
python3 dynamix_plots.py data metrics_schema.json
```

**With real data:** skip step 1. Empty `data/`, copy in the real
`run_metadata.csv` + `timeseries_*.csv` + `rebalance_*.csv` (schema per
`metrics_schema.md`), then run steps 2–3. If a file violates the contract,
the loader raises `SchemaError` naming the offending column/run.

---

## Figures → paper section

| fig | shows | primary group |
|---|---|---|
| **F1** | Throughput vs offered load, timeseries per condition | G1 |
| **F2** | p95 latency (bar + CDF) across conditions | G1 |
| **F3** | Resource footprint (supervisor pods + executors) | G1 |
| **F4** | Settling time + rebalance counts | G1 |
| **F5** | ARiSto formula ablation (old cumulative vs windowed) | G2 |
| **F6** | Parameter sensitivity (window / wscale / bolt-cap) | G3 |

F1–F4 + T1 are what make **Section V** writable (the P0 gap). F5/T2 justify
the throughput-formula fix; F6/T3 justify the parameter choices.

---

## Review-log traceability

Each priority item from the review log maps to a concrete deliverable here.
The full table lives at the end of `runbook.md` ("Mapping to the review
log"). Headline items:

- **P0** — 4-condition comparison → Group 1 → F1–F4 + T1 → Section V.
- **P1** — parameter sensitivity → Group 3 → F6 + T3.
- **P1** — controller-interaction safety → draft §III.D + cooldown /
  serialisation described in `metrics_schema.md` §4 and G1 KEDA setup.
- **P2** — throughput-formula justification → Group 2 → F5 + T2.
- **P2** — `weight_scale` weighting → G3 sweeps + `metrics_schema.md` §4.

(De-Vietnamising the draft and adding English figure labels is a P0
editing pass, not an experiment — flagged in the runbook but out of scope
for this code bundle.)

---

## Data contract in one paragraph

Three CSVs per campaign, sharing one `run_metadata.csv`.
`timeseries_<run_id>.csv` samples every 15 s (offered load, acked
throughput, emitted rate, complete latency, max bolt capacity, executor /
worker / supervisor-pod counts, `weight_scale`, CPU util).
`rebalance_<run_id>.csv` has one row per scaling action (layer =
aristo|keda, action = scale_out|scale_in, component, from/to counts,
trigger value). `run_id` convention: `<group>-<condition>-r<replicate>`
(e.g. `G1-dynamix-r1`, `G3-window_s=900-r1`). Baseline params: window 600 s,
wscale threshold 0.75, bolt-cap threshold 0.70, cooldown 300 s. Full
detail in `metrics_schema.md`.
