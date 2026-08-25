#!/usr/bin/env python3
"""
g1_throughput_diagnostic.py — DIAGNOSTIC throughput/latency chart for G1, NOT a
publication figure. Plots raw per-15s samples (no smoothing, no mean-across-
replicates) so the zero-collapse / spike pattern is visible as-is, to help
debug it rather than hide it.

Do not put this in the paper as-is: throughput/latency currently collapses to
zero for extended stretches in every condition (static, aristo_only, dynamix),
interspersed with isolated huge spikes that are almost certainly artifacts of
the 1-minute rate() window used by export_run.py's throughput_acked_per_s query
hitting a burst of delayed acks, not real sustained throughput. See chat log
2026-08-08 for the audit that found this.

Usage:
    scripts/venv/bin/python3 analysis/g1_throughput_diagnostic.py
"""
from __future__ import annotations
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import figstyle

figstyle.apply_figure_style(frame="open")

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "scripts", "docs", "experiment-results", "G1")
WINDOW_CAP_S = 1800
COLOR = {"static": "#2a78d6", "aristo_only": "#eb6834", "dynamix": "#1baf7a"}
LABEL = {"static": "Static", "aristo_only": "ARiSto-only", "dynamix": "DynamiX"}
RUN = {"static": "r3", "aristo_only": "r3", "dynamix": "r3"}


def _series(cond, col, cap=WINDOW_CAP_S):
    f = os.path.join(ROOT, cond, f"timeseries_G1-{cond}-{RUN[cond]}.csv")
    t, v = [], []
    for r in csv.DictReader(open(f)):
        raw = r.get(col, "")
        if raw in ("", None):
            continue
        try:
            t_s = float(r["t_s"])
        except (KeyError, ValueError):
            continue
        if t_s > cap:
            break
        try:
            v.append(float(raw)); t.append(t_s / 60.0)
        except ValueError:
            continue
    return t, v


def render():
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.8))
    conds = ["static", "aristo_only", "dynamix"]

    ax = axes[0]
    for c in conds:
        t, v = _series(c, "throughput_acked_per_s")
        ax.plot(t, v, color=COLOR[c], lw=1.0, marker="o", ms=1.8, alpha=0.85,
                 label=LABEL[c])
    ax.set_title("Acked throughput (raw, 15s samples)", loc="left", fontsize=9)
    ax.set_xlabel("Time (min)"); ax.set_ylabel("msg/s")
    ax.legend(frameon=False, fontsize=6.5, loc="upper right")
    figstyle.set_frame(ax, "open")

    ax = axes[1]
    for c in conds:
        t, v = _series(c, "complete_latency_ms")
        ax.plot(t, v, color=COLOR[c], lw=1.0, marker="o", ms=1.8, alpha=0.85,
                 label=LABEL[c])
    ax.set_yscale("symlog", linthresh=100)  # spikes reach 14,000ms; steady state is ~10-100ms
    ax.set_title("Complete latency, symlog y (raw, 15s samples)", loc="left", fontsize=9)
    ax.set_xlabel("Time (min)"); ax.set_ylabel("ms (symlog)")
    figstyle.set_frame(ax, "open")

    fig.suptitle("DIAGNOSTIC — G1 throughput/latency, NOT a publication figure "
                  "(raw samples, all conditions still collapse to zero intermittently)",
                  y=1.06, fontsize=9.5, fontweight="bold", color="#a63d1f")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "figures", "G1_throughput_DIAGNOSTIC_do_not_use_in_paper.png")
    fig.savefig(out, dpi=300, bbox_inches="tight")
    print(f"wrote {out}")

    print("\ncondition    zero-throughput samples / total   max single-sample spike")
    for c in conds:
        t, v = _series(c, "throughput_acked_per_s")
        n_zero = sum(1 for x in v if x == 0.0)
        print(f"{c:12s}  {n_zero:3d} / {len(v):3d}  ({100*n_zero/len(v):.0f}%)          max={max(v):.0f} msg/s")


if __name__ == "__main__":
    render()
