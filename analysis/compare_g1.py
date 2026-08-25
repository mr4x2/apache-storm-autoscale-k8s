#!/usr/bin/env python3
"""
compare_g1.py — focused Static vs ARiSto-only vs DynamiX comparison (G1).

Drops keda_only and plots the three conditions that answer "is DynamiX worth it":
  (1) throughput tracking vs offered load over time,
  (2) complete latency over time,
  (3) bar summary at the top load step: sustained throughput + p95 latency.

Reuses the same loader + house style as dynamix_plots.py so it stays consistent
with F1-F6. Writes analysis/figures/G1_compare_static_aristo_dynamix.png.

Usage:
    scripts/venv/bin/python3 analysis/compare_g1.py <data_dir> [schema.json]
    # default data_dir = analysis/data (SYNTHETIC), schema = metrics_schema.json
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import figstyle
import dynamix_analysis as da

figstyle.apply_figure_style(frame="open")

CONDS = ["static", "aristo_only", "dynamix"]
COLOR = {"static": "#9e9e9e", "aristo_only": "#f58518", "dynamix": "#54a24b"}
LABEL = {"static": "Static", "aristo_only": "ARiSto-only", "dynamix": "DynamiX"}


def _mean_trace(camp, condition, col):
    d = camp.ts(group="G1", condition=condition)
    if d.empty:
        return None, None, None
    piv = d.pivot_table(index="t_s", columns="run_id", values=col, aggfunc="mean")
    t = piv.index.to_numpy() / 60.0
    m = piv.mean(axis=1).to_numpy()
    sd = piv.std(axis=1).to_numpy() if piv.shape[1] > 1 else np.zeros_like(m)
    return t, m, sd


def _load_shading(ax, camp):
    steps = da.load_steps(camp.schema)
    for _, s in steps.iterrows():
        if int(s.level) % 2 == 0:
            ax.axvspan(s.t_start / 60, s.t_end / 60, color="#000000", alpha=0.04, lw=0, zorder=0)
        ax.axvline(s.t_start / 60, color=figstyle.META_GREY, lw=0.5, ls=":", zorder=1)


def render(camp, outdir="figures"):
    os.makedirs(outdir, exist_ok=True)
    fig = plt.figure(figsize=(11, 4.2))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.15, 1.15, 1.0], wspace=0.32)
    ax_tp, ax_lat, ax_bar = fig.add_subplot(gs[0]), fig.add_subplot(gs[1]), fig.add_subplot(gs[2])

    # ---- (1) throughput over time + offered-load reference ----
    _load_shading(ax_tp, camp)
    off_t, off_m, _ = _mean_trace(camp, "dynamix", "offered_load_msgs_per_s")
    if off_t is not None:
        ax_tp.plot(off_t, off_m, color="#333333", lw=1.1, ls="--", label="Offered load", zorder=2)
    for c in CONDS:
        t, m, sd = _mean_trace(camp, c, "throughput_acked_per_s")
        if t is None:
            continue
        ax_tp.plot(t, m, color=COLOR[c], lw=1.6, label=LABEL[c], zorder=3)
        ax_tp.fill_between(t, m - sd, m + sd, color=COLOR[c], alpha=0.15, lw=0)
    ax_tp.set_xlabel("Time (min)")
    ax_tp.set_ylabel("Throughput (acked msg/s)")
    ax_tp.set_title("(a) Throughput vs offered load", loc="left")
    ax_tp.legend(frameon=False, fontsize=7, loc="upper left")

    # ---- (2) latency over time ----
    _load_shading(ax_lat, camp)
    for c in CONDS:
        t, m, sd = _mean_trace(camp, c, "complete_latency_ms")
        if t is None:
            continue
        ax_lat.plot(t, m, color=COLOR[c], lw=1.6, label=LABEL[c], zorder=3)
        ax_lat.fill_between(t, m - sd, m + sd, color=COLOR[c], alpha=0.15, lw=0)
    ax_lat.set_xlabel("Time (min)")
    ax_lat.set_ylabel("Complete latency (ms)")
    ax_lat.set_title("(b) End-to-end latency", loc="left")
    ax_lat.legend(frameon=False, fontsize=7, loc="upper left")

    # ---- (3) top-load-step bar: sustained throughput + p95 latency ----
    g1 = camp.group1_summary() if hasattr(camp, "group1_summary") else None
    top = da.load_steps(camp.schema)["level"].max()
    x = np.arange(len(CONDS))
    tp_vals, lat_vals = [], []
    for c in CONDS:
        d = camp.ts(group="G1", condition=c)
        top_load = da.load_steps(camp.schema)
        top_load = top_load[top_load.level == top]
        t0, t1 = float(top_load.t_start.iloc[0]), float(top_load.t_end.iloc[0])
        seg = d[(d.t_s >= t0) & (d.t_s <= t1)]
        tp_vals.append(seg["throughput_acked_per_s"].mean() if not seg.empty else np.nan)
        lat_vals.append(seg["complete_latency_ms"].quantile(0.95) if not seg.empty else np.nan)

    ax_bar.bar(x, tp_vals, color=[COLOR[c] for c in CONDS], width=0.62)
    ax_bar.set_xticks(x)
    ax_bar.set_xticklabels([LABEL[c] for c in CONDS], rotation=15)
    ax_bar.set_ylabel("Sustained throughput (msg/s)")
    ax_bar.set_title(f"(c) At top load step", loc="left")
    for xi, v, lv in zip(x, tp_vals, lat_vals):
        if not np.isnan(v):
            ax_bar.text(xi, v, f"{v:,.0f}\np95 {lv:.0f}ms", ha="center", va="bottom", fontsize=6.5)
    ax_bar.margins(y=0.18)

    fig.suptitle("G1 — Static vs ARiSto-only vs DynamiX", y=1.02, fontsize=11, fontweight="bold")
    out = os.path.join(outdir, "G1_compare_static_aristo_dynamix.png")
    fig.savefig(out, dpi=300, bbox_inches="tight")
    print(f"wrote {out}")
    return out


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    schema = sys.argv[2] if len(sys.argv) > 2 else "metrics_schema.json"
    camp = da.load_campaign(data_dir, schema)
    render(camp, outdir=os.path.join(os.path.dirname(data_dir) or ".", "figures")
           if data_dir != "data" else "figures")
