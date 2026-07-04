# analysis/ — DynamiX experiment analysis & figures

Turns experiment-run CSVs into the paper's Section V summary tables and
figures. Validated end-to-end; **no per-run editing** — the interface is fixed
by the data contract in [`../docs/metrics-schema.md`](../docs/metrics-schema.md)
(machine-readable: [`../docs/metrics-schema.json`](../docs/metrics-schema.json)).

The experiment procedures that produce these CSVs live in
[`../docs/experiments.md`](../docs/experiments.md).

## Files

| file | role |
|---|---|
| `dynamix_analysis.py` | load + schema-validate runs; derive per-level metrics (throughput, p95/p99 latency, settling time, CoV, rebalance counts, saturation gap); write `tables/group{1,2,3}_summary.csv` |
| `dynamix_plots.py` | render F1–F6 (300-dpi PNGs, English labels) into `figures/` |
| `make_synthetic_runs.py` | **placeholder data generator** for dry-runs before the cluster is ready — see warning below |
| `figstyle.py` | publication figure-style helper |

## Run

```bash
cd analysis

# Dry-run against fabricated data (proves the pipeline; NOT real results):
python3 make_synthetic_runs.py --outdir data
python3 dynamix_analysis.py data          # schema path auto-resolves to ../docs/metrics-schema.json
python3 dynamix_plots.py    data

# Real data: point at the experiment-results tree instead
python3 dynamix_analysis.py ../docs/experiment-results
python3 dynamix_plots.py    ../docs/experiment-results
```

A file that violates the contract raises `SchemaError` naming the offending
run/column before it can reach a figure.

## ⚠️ Synthetic data is not results

`make_synthetic_runs.py` fabricates plausible runs so the code can be exercised
before the cluster exists. **The values it produces are made up.** `data/`,
`figures/`, and `tables/` are git-ignored for this reason. Before quoting any
number in the paper: empty `data/`, drop in real exported CSVs (schema per
`../docs/metrics-schema.md`), and re-run.

## Two blockers the code surfaced (see docs/experiments.md Phase 0)

1. **`OutputWriter` is not wired into `rulebase/v1/`** — until it is, the
   modified-v1 / DynamiX runs emit no `layer=aristo` rebalance rows, so F4 and
   the rebalance columns are blank for the headline P0 condition.
2. **`weight_scale` formula in the draft ≠ the code** — the controller
   (`k8s/keda/custom-metrics/main.py`) divides each signal by its threshold
   (0.70 / 0.50 / 100 ms) before weighting; reconcile the paper §III text.

## Figures

| fig | shows | feeds |
|---|---|---|
| F1 | throughput vs offered load, per condition | G1 → §V |
| F2 | p95 latency (bar + CDF) | G1 → §V |
| F3 | resource footprint (pods + executors) | G1 → §V |
| F4 | settling time + rebalance counts | G1 → §V |
| F5 | ARiSto formula ablation (windowed vs cumulative) | G2 → §III.C |
| F6 | parameter sensitivity (window / wscale / bolt-cap) | G3 → §V |

## Dependencies

`pandas`, `numpy`, `matplotlib`. `pip install pandas numpy matplotlib`.
