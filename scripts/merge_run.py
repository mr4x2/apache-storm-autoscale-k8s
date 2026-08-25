#!/usr/bin/env python3
"""
Merge the Storm/kubectl state columns (from storm_snapshot.py) into the
Prometheus timeseries (from export_run.py), producing one schema-complete
timeseries_<run_id>.csv.

export_run.py fills: throughput, latency, capacity, weight_scale, workers_total.
storm_snapshot.py fills: executors_total, supervisor_pods (and workers_total).

This does an as-of join on t_s (nearest sample within --tolerance seconds) and
writes back executors_total + supervisor_pods (and workers_total where the
Prometheus export left it blank). Result validates against metrics-schema.json.

Usage:
    scripts/venv/bin/python3 scripts/merge_run.py \
        --timeseries docs/experiment-results/G1/aristo_only/timeseries_G1-aristo_only-r1.csv \
        --state      docs/experiment-results/G1/aristo_only/state_G1-aristo_only-r1.csv

By default it overwrites the timeseries file in place. Pass --out to write elsewhere.

Requires: pandas (in scripts/venv).
"""
import argparse
import os
import sys

import pandas as pd

# columns owned by the state file that we push into the timeseries
STATE_COLS = ["executors_total", "supervisor_pods", "workers_total"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeseries", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--out", default=None, help="default: overwrite --timeseries")
    ap.add_argument("--tolerance", type=int, default=None,
                    help="max seconds between a timeseries row and the state "
                         "sample it borrows from (default: 2x median state step)")
    args = ap.parse_args()

    for p in (args.timeseries, args.state):
        if not os.path.isfile(p):
            print(f"ERROR: no such file: {p}", file=sys.stderr)
            sys.exit(1)

    ts = pd.read_csv(args.timeseries)
    st = pd.read_csv(args.state)
    ts["t_s"] = pd.to_numeric(ts["t_s"], errors="coerce").astype("Int64")
    st["t_s"] = pd.to_numeric(st["t_s"], errors="coerce").astype("Int64")
    ts = ts.dropna(subset=["t_s"]).sort_values("t_s").reset_index(drop=True)
    st = st.dropna(subset=["t_s"]).sort_values("t_s").reset_index(drop=True)

    if args.tolerance is None:
        steps = st["t_s"].astype(int).diff().dropna()
        med = int(steps.median()) if not steps.empty else 15
        tol = max(2 * med, 30)
    else:
        tol = args.tolerance

    have = [c for c in STATE_COLS if c in st.columns]
    right = st[["t_s"] + have].copy()
    right["t_s"] = right["t_s"].astype("int64")
    left = ts.copy()
    left["_t"] = left["t_s"].astype("int64")

    merged = pd.merge_asof(
        left.sort_values("_t"), right.sort_values("t_s"),
        left_on="_t", right_on="t_s", direction="nearest",
        tolerance=tol, suffixes=("", "_state"))

    for c in have:
        src = c if c in merged.columns else None
        # merge_asof suffixes the right column when a same-named left col exists
        state_col = c + "_state" if (c + "_state") in merged.columns else src
        if state_col is None:
            continue
        if c in ts.columns:
            # prefer existing non-empty timeseries value; else take state value
            existing = pd.to_numeric(ts[c], errors="coerce")
            filled = existing.where(existing.notna(), pd.to_numeric(merged[state_col], errors="coerce"))
            ts[c] = filled
        else:
            ts[c] = pd.to_numeric(merged[state_col], errors="coerce")

    # nullable-int formatting for count columns
    for c in ["executors_total", "supervisor_pods", "workers_total"]:
        if c in ts.columns:
            ts[c] = pd.to_numeric(ts[c], errors="coerce").astype("Int64")

    out_path = args.out or args.timeseries
    ts.to_csv(out_path, index=False)

    filled = {c: int(ts[c].notna().sum()) for c in have if c in ts.columns}
    print(f"Merged {len(st)} state rows into {len(ts)} timeseries rows "
          f"(tolerance={tol}s) → {out_path}")
    print(f"Filled non-null counts: {filled}")
    unmatched = [c for c in have if c in ts.columns and ts[c].isna().all()]
    if unmatched:
        print(f"WARNING: still all-empty after merge: {unmatched} "
              f"(t_s ranges may not overlap; check --t0 alignment)", file=sys.stderr)


if __name__ == "__main__":
    main()
