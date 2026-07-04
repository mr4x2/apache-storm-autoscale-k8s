"""
dynamix_analysis.py — load + validate + derive metrics for the DynamiX autoscaling
experiments (Groups 1-3).

Pure analysis: loaders that validate incoming CSVs against metrics_schema.json,
metric-derivation functions, and per-group summary-table builders. No plotting.

Usage
-----
    import dynamix_analysis as da
    ds   = da.load_campaign("data", schema="metrics_schema.json")   # -> Campaign
    g1   = da.summarize_group1(ds); g1.to_csv("tables/group1_summary.csv", index=False)
    g2   = da.summarize_group2(ds); g3 = da.summarize_group3(ds)

All functions return tidy pandas DataFrames. Every loader raises SchemaError with
the offending file/column/row if a file does not conform to the contract.
"""
from __future__ import annotations
import json, os, glob, math
from dataclasses import dataclass, field
import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Schema handling / validation
# --------------------------------------------------------------------------- #
class SchemaError(ValueError):
    """Raised when a data file violates metrics_schema.json."""

_DTYPE_CHECK = {
    "str":   lambda s: True,                              # everything coerces to str
    "int":   lambda s: _coercible_numeric(s),
    "float": lambda s: _coercible_numeric(s),
}

def _coercible_numeric(s: pd.Series) -> bool:
    v = pd.to_numeric(s, errors="coerce")
    # allow NaNs (nullable columns); require that non-null originals stay non-null
    orig_nonnull = s.notna() & (s.astype(str).str.strip() != "")
    return bool((~(orig_nonnull & v.isna())).all())

def load_schema(path: str = "metrics_schema.json") -> dict:
    with open(path) as f:
        return json.load(f)

def _validate_columns(df: pd.DataFrame, spec: dict, fname: str) -> pd.DataFrame:
    """Check required columns exist and are dtype-coercible; coerce numeric cols."""
    cols = spec["columns"]
    missing = [c["name"] for c in cols if c["name"] not in df.columns]
    if missing:
        raise SchemaError(f"{fname}: missing required columns {missing}")
    for c in cols:
        name, dt = c["name"], c["dtype"]
        if not _DTYPE_CHECK[dt](df[name]):
            bad = df.loc[pd.to_numeric(df[name], errors="coerce").isna() & df[name].notna(), name]
            raise SchemaError(f"{fname}: column '{name}' not coercible to {dt}; "
                              f"first bad value: {bad.iloc[0]!r} at row {bad.index[0]}")
        if dt in ("int", "float"):
            df[name] = pd.to_numeric(df[name], errors="coerce")
            if dt == "int":
                df[name] = df[name].astype("Int64")  # nullable int
    return df

# --------------------------------------------------------------------------- #
# Campaign container
# --------------------------------------------------------------------------- #
@dataclass
class Campaign:
    timeseries: pd.DataFrame            # concat of all timeseries_*.csv
    rebalance:  pd.DataFrame            # concat of all rebalance_*.csv
    metadata:   pd.DataFrame            # run_metadata.csv
    schema:     dict = field(repr=False, default_factory=dict)

    def ts(self, group=None, condition=None) -> pd.DataFrame:
        d = self.timeseries
        if group is not None:     d = d[d["group"] == group]
        if condition is not None: d = d[d["condition"] == condition]
        return d

    @property
    def run_ids(self):
        return sorted(self.timeseries["run_id"].unique())

def load_campaign(data_dir: str, schema: str = "metrics_schema.json") -> Campaign:
    sch = load_schema(schema)
    sf  = sch["files"]

    # metadata (one shared file)
    meta_path = os.path.join(data_dir, "run_metadata.csv")
    if not os.path.exists(meta_path):
        raise SchemaError(f"missing {meta_path}")
    meta = _validate_columns(pd.read_csv(meta_path), sf["run_metadata"], "run_metadata.csv")

    ts_frames, rb_frames = [], []
    for p in sorted(glob.glob(os.path.join(data_dir, "timeseries_*.csv"))):
        df = _validate_columns(pd.read_csv(p), sf["timeseries"], os.path.basename(p))
        _validate_timeseries_rows(df, os.path.basename(p), sch)
        ts_frames.append(df)
    for p in sorted(glob.glob(os.path.join(data_dir, "rebalance_*.csv"))):
        df = pd.read_csv(p)
        if len(df):  # header-only (static) is valid
            df = _validate_columns(df, sf["rebalance_events"], os.path.basename(p))
        rb_frames.append(df)

    if not ts_frames:
        raise SchemaError(f"no timeseries_*.csv found in {data_dir}")
    ts = pd.concat(ts_frames, ignore_index=True)
    rb_nonempty = [d for d in rb_frames if len(d)]
    rb = pd.concat(rb_nonempty, ignore_index=True) if rb_nonempty else pd.DataFrame(
        columns=[c["name"] for c in sf["rebalance_events"]["columns"]])

    # cross-file: every run_id in timeseries must exist in metadata
    orphan = set(ts["run_id"]) - set(meta["run_id"])
    if orphan:
        raise SchemaError(f"run_ids in timeseries missing from run_metadata.csv: {sorted(orphan)}")
    return Campaign(timeseries=ts, rebalance=rb, metadata=meta, schema=sch)

def _validate_timeseries_rows(df: pd.DataFrame, fname: str, sch: dict):
    period = sch["files"]["timeseries"]["sample_period_s"]
    for rid, g in df.groupby("run_id"):
        t = pd.to_numeric(g["t_s"], errors="coerce").to_numpy()
        if np.any(np.diff(t) < 0):
            raise SchemaError(f"{fname}: t_s not monotonic non-decreasing for run {rid}")
        gaps = np.diff(t)
        if len(gaps) and np.nanmax(gaps) > 2 * period:
            raise SchemaError(f"{fname}: sample gap {np.nanmax(gaps):.0f}s > 2x period "
                              f"({2*period}s) for run {rid}")

# --------------------------------------------------------------------------- #
# Load-step segmentation
# --------------------------------------------------------------------------- #
def load_steps(schema: dict) -> pd.DataFrame:
    """Return the load profile as a frame of [level, load, t_start, t_end]."""
    steps = schema["load_profile_default"]["steps"]
    rows, t0 = [], 0
    for s in steps:
        rows.append({"level": s["level"], "offered_load_msgs_per_s": s["offered_load_msgs_per_s"],
                     "t_start": t0, "t_end": t0 + s["duration_s"]})
        t0 += s["duration_s"]
    return pd.DataFrame(rows)

def steady_state_mask(t_s, t_start, t_end, tail_frac=0.5):
    """Boolean mask selecting the trailing `tail_frac` of a load step's window
    (steady state after the scaler has reacted)."""
    span = t_end - t_start
    lo = t_start + (1 - tail_frac) * span
    return (t_s >= lo) & (t_s < t_end)

# --------------------------------------------------------------------------- #
# Core metric derivations (per run x load-level)
# --------------------------------------------------------------------------- #
def _cov(x):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    m = x.mean()
    return float(x.std(ddof=1) / m) if len(x) > 1 and m != 0 else np.nan

def _pct(x, q):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    return float(np.percentile(x, q)) if len(x) else np.nan

def per_level_metrics(camp: Campaign, warmup_s: int | None = None) -> pd.DataFrame:
    """One row per (run_id, load level): steady-state throughput mean/CoV,
    latency percentiles, saturation gap."""
    steps = load_steps(camp.schema)
    out = []
    for rid, g in camp.timeseries.groupby("run_id"):
        g = g.sort_values("t_s")
        meta = camp.metadata.loc[camp.metadata["run_id"] == rid]
        wu = int(meta["warmup_s"].iloc[0]) if (warmup_s is None and len(meta)) else (warmup_s or 0)
        t = g["t_s"].to_numpy()
        for _, s in steps.iterrows():
            m = steady_state_mask(t, s.t_start, s.t_end) & (t >= wu)
            gg = g[m]
            if gg.empty:
                continue
            acked = gg["throughput_acked_per_s"].to_numpy(float)
            offered = s.offered_load_msgs_per_s
            out.append({
                "run_id": rid, "group": g["group"].iloc[0], "condition": g["condition"].iloc[0],
                "level": int(s.level), "offered_load_msgs_per_s": offered,
                "throughput_mean": float(np.nanmean(acked)),
                "throughput_cov": _cov(acked),
                "latency_p50": _pct(gg["complete_latency_ms"], 50),
                "latency_p95": _pct(gg["complete_latency_ms"], 95),
                "latency_p99": _pct(gg["complete_latency_ms"], 99),
                "supervisor_pods_end": float(gg["supervisor_pods"].dropna().iloc[-1]) if gg["supervisor_pods"].notna().any() else np.nan,
                "executors_end": float(gg["executors_total"].dropna().iloc[-1]) if gg["executors_total"].notna().any() else np.nan,
                "saturation_gap": float(offered - np.nanmean(acked)),
            })
    return pd.DataFrame(out)

def settling_time(camp: Campaign, run_id: str, tol=0.05) -> pd.DataFrame:
    """For each load step (after the first), seconds from step onset until acked
    throughput enters and stays within +/- tol of the step's steady-state mean.
    Returns NaN (censored) if it never settles within the step window."""
    steps = load_steps(camp.schema)
    g = camp.timeseries[camp.timeseries["run_id"] == run_id].sort_values("t_s")
    t = g["t_s"].to_numpy(); y = g["throughput_acked_per_s"].to_numpy(float)
    rows = []
    for _, s in steps.iterrows():
        seg = (t >= s.t_start) & (t < s.t_end)
        ss_mask = steady_state_mask(t, s.t_start, s.t_end)
        if not ss_mask.any():
            rows.append({"run_id": run_id, "level": int(s.level), "settling_time_s": np.nan}); continue
        target = np.nanmean(y[ss_mask])
        band = tol * target
        settled = np.nan
        idxs = np.where(seg)[0]
        for i in idxs:
            # settled = from here to end-of-step all within band
            tail = idxs[idxs >= i]
            if np.all(np.abs(y[tail] - target) <= band):
                settled = float(t[i] - s.t_start); break
        rows.append({"run_id": run_id, "level": int(s.level),
                     "settling_time_s": settled, "target_throughput": float(target)})
    return pd.DataFrame(rows)

def rebalance_counts(camp: Campaign) -> pd.DataFrame:
    """Per run_id: count of scaling actions by layer and direction."""
    rb = camp.rebalance
    base = camp.metadata[["run_id", "group", "condition"]].copy()
    if rb.empty:
        for c in ["aristo_scale_out","aristo_scale_in","keda_scale_out","keda_scale_in","total_rebalances"]:
            base[c] = 0
        return base
    def _cnt(df, layer, action):
        return ((df["layer"] == layer) & (df["action"] == action)).sum()
    rows = []
    for rid, g in rb.groupby("run_id"):
        rows.append({"run_id": rid,
                     "aristo_scale_out": _cnt(g,"aristo","scale_out"),
                     "aristo_scale_in":  _cnt(g,"aristo","scale_in"),
                     "keda_scale_out":   _cnt(g,"keda","scale_out"),
                     "keda_scale_in":    _cnt(g,"keda","scale_in"),
                     "total_rebalances": len(g)})
    counts = pd.DataFrame(rows)
    out = base.merge(counts, on="run_id", how="left")
    fillc = ["aristo_scale_out","aristo_scale_in","keda_scale_out","keda_scale_in","total_rebalances"]
    out[fillc] = out[fillc].fillna(0).astype(int)
    return out

def _agg_mean_ci(s: pd.Series):
    """mean and 95% t-CI half-width across replicates."""
    x = s.dropna().to_numpy(float); n = len(x)
    if n == 0: return (np.nan, np.nan, 0)
    m = x.mean()
    if n == 1: return (m, np.nan, 1)
    # t_{0.975, n-1} without scipy: small-n table + normal fallback
    tcrit = {1:12.706,2:4.303,3:3.182,4:2.776,5:2.571,6:2.447,7:2.365,8:2.306,9:2.262}.get(n-1, 1.96)
    hw = tcrit * x.std(ddof=1) / math.sqrt(n)
    return (m, hw, n)

# --------------------------------------------------------------------------- #
# Group summary tables (aggregate across replicates)
# --------------------------------------------------------------------------- #
_COND_ORDER = ["static", "keda_only", "aristo_only", "dynamix"]

def summarize_group1(camp: Campaign) -> pd.DataFrame:
    """T1: per-condition x load-level steady-state stats, aggregated over replicates."""
    plm = per_level_metrics(camp)
    plm = plm[plm["group"] == "G1"]
    rc  = rebalance_counts(camp); rc = rc[rc["group"] == "G1"]
    settle = pd.concat([settling_time(camp, rid) for rid in plm["run_id"].unique()], ignore_index=True) \
             if len(plm) else pd.DataFrame(columns=["run_id","level","settling_time_s"])
    settle = settle.merge(camp.metadata[["run_id","condition"]], on="run_id", how="left")

    rows = []
    for cond in [c for c in _COND_ORDER if c in plm["condition"].unique()]:
        for lvl in sorted(plm["level"].unique()):
            sub = plm[(plm["condition"] == cond) & (plm["level"] == lvl)]
            tm, tci, n = _agg_mean_ci(sub["throughput_mean"])
            st = settle[(settle["condition"] == cond) & (settle["level"] == lvl)]["settling_time_s"]
            stm, stci, _ = _agg_mean_ci(st)
            rows.append({
                "condition": cond, "level": lvl,
                "offered_load": sub["offered_load_msgs_per_s"].iloc[0] if len(sub) else np.nan,
                "n_replicates": n,
                "throughput_mean": tm, "throughput_ci95": tci,
                "throughput_cov_mean": sub["throughput_cov"].mean(),
                "latency_p95_mean": sub["latency_p95"].mean(),
                "latency_p99_mean": sub["latency_p99"].mean(),
                "saturation_gap_mean": sub["saturation_gap"].mean(),
                "settling_time_s_mean": stm, "settling_time_s_ci95": stci,
                "supervisor_pods_end_mean": sub["supervisor_pods_end"].mean(),
            })
    df = pd.DataFrame(rows)
    # attach total rebalances per condition (run-level, load-independent)
    rb_by_cond = rc.groupby("condition")["total_rebalances"].mean().rename("rebalances_mean")
    df = df.merge(rb_by_cond, on="condition", how="left")
    return df

def summarize_group2(camp: Campaign) -> pd.DataFrame:
    """G2: modified vs original ARiSto v1 — throughput + rebalances + under-scale flag."""
    plm = per_level_metrics(camp); plm = plm[plm["group"] == "G2"]
    rc  = rebalance_counts(camp);  rc  = rc[rc["group"] == "G2"]
    rows = []
    for cond in sorted(plm["condition"].unique()):
        for lvl in sorted(plm["level"].unique()):
            sub = plm[(plm["condition"] == cond) & (plm["level"] == lvl)]
            tm, tci, n = _agg_mean_ci(sub["throughput_mean"])
            rows.append({"condition": cond, "level": lvl,
                         "offered_load": sub["offered_load_msgs_per_s"].iloc[0] if len(sub) else np.nan,
                         "n_replicates": n, "throughput_mean": tm, "throughput_ci95": tci,
                         "saturation_gap_mean": sub["saturation_gap"].mean()})
    df = pd.DataFrame(rows)
    rbm = rc.groupby("condition")["aristo_scale_out"].mean().rename("aristo_scale_out_mean")
    df = df.merge(rbm, on="condition", how="left")
    # under-scale flag: at top load, does mean throughput fall well short of offered?
    top = df["level"].max() if len(df) else None
    df["under_scale_flag"] = np.where(
        (df["level"] == top) & (df["saturation_gap_mean"] > 0.25 * df["offered_load"]), True, False)
    return df

def summarize_group3(camp: Campaign) -> pd.DataFrame:
    """G3: per swept-parameter value at top load — stability (CoV) + rebalance freq."""
    plm = per_level_metrics(camp); plm = plm[plm["group"] == "G3"]
    rc  = rebalance_counts(camp);  rc  = rc[rc["group"] == "G3"]
    meta = camp.metadata.copy()
    meta["params"] = meta["params_json"].apply(lambda s: json.loads(s) if isinstance(s, str) and s.strip().startswith("{") else {})
    top = plm["level"].max() if len(plm) else None
    plm_top = plm[plm["level"] == top].merge(meta[["run_id","params"]], on="run_id", how="left")
    rc = rc.merge(meta[["run_id","params"]], on="run_id", how="left")

    rows = []
    for knob in ["window_s", "wscale_threshold", "bolt_cap_threshold"]:
        # a run belongs to a knob's sweep if its condition names that knob OR it is the shared baseline
        def knob_val(p): return p.get(knob)
        sub = plm_top.copy(); sub["knob_val"] = sub["params"].apply(knob_val)
        subr = rc.copy();     subr["knob_val"] = subr["params"].apply(knob_val)
        sub = sub[sub["condition"].str.contains(knob) | (sub["condition"] == "baseline")]
        subr = subr[subr["condition"].str.contains(knob) | (subr["condition"] == "baseline")]
        for val in sorted(v for v in sub["knob_val"].dropna().unique()):
            s2 = sub[sub["knob_val"] == val]; r2 = subr[subr["knob_val"] == val]
            tm, tci, n = _agg_mean_ci(s2["throughput_mean"])
            rows.append({"knob": knob, "knob_val": val, "n_replicates": n,
                         "throughput_mean": tm, "throughput_ci95": tci,
                         "throughput_cov_mean": s2["throughput_cov"].mean(),
                         "latency_p95_mean": s2["latency_p95"].mean(),
                         "rebalance_freq_mean": r2["total_rebalances"].mean()})
    return pd.DataFrame(rows)

def write_all_summaries(camp: Campaign, outdir: str = "tables") -> dict:
    os.makedirs(outdir, exist_ok=True)
    paths = {}
    for name, fn in [("group1_summary", summarize_group1),
                     ("group2_summary", summarize_group2),
                     ("group3_summary", summarize_group3)]:
        try:
            df = fn(camp)
        except Exception as e:
            df = pd.DataFrame({"error": [str(e)]})
        p = os.path.join(outdir, f"{name}.csv"); df.to_csv(p, index=False); paths[name] = p
    return paths

if __name__ == "__main__":
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else "data"
    schema = sys.argv[2] if len(sys.argv) > 2 else "metrics_schema.json"
    camp = load_campaign(d, schema)
    print(f"loaded {len(camp.run_ids)} runs, {len(camp.timeseries)} samples, "
          f"{len(camp.rebalance)} rebalance events")
    paths = write_all_summaries(camp)
    print("wrote:", paths)
