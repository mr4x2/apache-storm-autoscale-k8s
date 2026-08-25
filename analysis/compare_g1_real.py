#!/usr/bin/env python3
"""
compare_g1_real.py — REAL-data G1 comparison from the state pollers.

Uses the VALID metrics only: the autoscaler-behavior columns (supervisor_pods,
workers_total, executors_total) from state_<run>.csv, which are ground truth from
the Storm REST + kubectl poller. Throughput/latency are DELIBERATELY excluded:
the real runs saturate at ~600 msg/s regardless of condition (acking ceiling),
so throughput is not a valid comparison metric yet.

Reads scripts/docs/experiment-results/G1/<condition>/state_*.csv and
rebalance_*.csv. n=1 for dynamix/keda_only — treat as illustrative, not
statistically significant.

Conditions are NOT guaranteed to cover the same wall-clock t_s range — e.g.
dynamix may need to run/settle longer than static/aristo_only because pod-level
(KEDA) scaling reacts slower than the fixed 30-min load ramp used elsewhere.
Comparing raw full-range series would let the longer run's extra tail skew the
comparison. --window-cap fixes the x-axis/summary to a single common range so
every condition is compared over the same window; anything beyond the cap is
still in the source files and can be inspected separately, it's just excluded
from this comparison.

Usage:
    scripts/venv/bin/python3 analysis/compare_g1_real.py
    scripts/venv/bin/python3 analysis/compare_g1_real.py --window-cap 1800   # seconds
    scripts/venv/bin/python3 analysis/compare_g1_real.py --window-cap auto  # default: shortest condition's max t_s
"""
from __future__ import annotations
import argparse, csv, glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import figstyle

figstyle.apply_figure_style(frame="open")

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "scripts", "docs", "experiment-results", "G1")
CONDS = ["static", "aristo_only", "dynamix"]
COLOR = {"static": "#9e9e9e", "keda_only": "#4c78a8",
         "aristo_only": "#f58518", "dynamix": "#54a24b"}
LABEL = {"static": "Static", "keda_only": "KEDA-only",
         "aristo_only": "ARiSto-only", "dynamix": "DynamiX"}


def _raw_rows(cond, kind):
    """kind: 'state' or 'timeseries'/'rebalance'. Returns list[dict] with raw t_s (seconds, str)."""
    if kind == "state":
        f = os.path.join(ROOT, cond, f"state_G1-{cond}-r1.csv")
        if not os.path.isfile(f):  # static: no poller, use timeseries
            g = glob.glob(os.path.join(ROOT, cond, "timeseries_*.csv"))
            if not g:
                return []
            f = sorted(g)[0]
    else:
        f = os.path.join(ROOT, cond, f"rebalance_G1-{cond}-r1.csv")
        if not os.path.isfile(f):
            return []
    return list(csv.DictReader(open(f)))


def _max_t_s(cond):
    rows = _raw_rows(cond, "state")
    vals = [float(r["t_s"]) for r in rows if r.get("t_s") not in ("", None)]
    return max(vals) if vals else None


def resolve_window_cap(arg, conds=CONDS):
    """None -> no cap. 'auto' -> min of each present condition's max t_s
    (i.e. cap to whichever condition ran/settled for the shortest time).
    Otherwise a fixed number of seconds."""
    if arg is None:
        return None
    if arg != "auto":
        return float(arg)
    maxima = [_max_t_s(c) for c in conds]
    maxima = [m for m in maxima if m is not None]
    return min(maxima) if maxima else None


def _series(cond, col, cap=None):
    """(t_min, values) from the state CSV; falls back to timeseries for static.
    cap: if set, rows with t_s > cap (seconds) are dropped."""
    t, v = [], []
    for r in _raw_rows(cond, "state"):
        raw = r.get(col, "")
        if raw in ("", None):
            continue
        try:
            t_s = float(r["t_s"])
        except (ValueError, KeyError):
            continue
        if cap is not None and t_s > cap:
            continue
        try:
            v.append(float(raw)); t.append(t_s / 60.0)
        except ValueError:
            continue
    return t, v


def _rebalances(cond, cap=None):
    out = []
    for r in _raw_rows(cond, "rebalance"):
        try:
            t_s = float(r["t_s"])
        except (ValueError, KeyError):
            continue
        if cap is not None and t_s > cap:
            continue
        out.append((t_s / 60.0, r["layer"], r["action"]))
    return out


def render(cap=None):
    # transparency: report each condition's true max t_s vs. what the cap kept,
    # so a truncated tail (e.g. dynamix settling past the other conditions'
    # capture window) is visible in the output, not silently dropped.
    print("condition    full max t_s   used for comparison")
    for c in CONDS:
        full_max = _max_t_s(c)
        used = min(full_max, cap) if (full_max is not None and cap is not None) else full_max
        flag = "  <- TRUNCATED" if (cap is not None and full_max is not None and full_max > cap) else ""
        print(f"{c:12s} {full_max!s:14s} {used!s:14s}{flag}")
    if cap is not None:
        print(f"window-cap = {cap:g}s ({cap/60:g} min)\n")
    else:
        print("window-cap = none (full raw range per condition — NOT apples-to-apples if durations differ)\n")

    fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharex=True)
    specs = [("supervisor_pods", "Supervisor pods (infra layer / KEDA)"),
             ("workers_total", "Storm workers (topology layer / ARiSto)"),
             ("executors_total", "Executors total (topology layer / ARiSto)")]
    for ax, (col, title) in zip(axes, specs):
        for c in CONDS:
            t, v = _series(c, col, cap=cap)
            if not t:
                continue
            ax.step(t, v, where="post", color=COLOR[c], lw=1.7,
                    label=LABEL[c], zorder=3)
        ax.set_title(title, loc="left", fontsize=9)
        ax.set_xlabel("Time (min)")
        ax.margins(y=0.15)
    axes[0].set_ylabel("count")
    axes[0].legend(frameon=False, fontsize=7, loc="upper left")

    # mark keda supervisor scale events on panel 0 (the DynamiX differentiator)
    for c in CONDS:
        for tm, layer, action in _rebalances(c, cap=cap):
            if layer == "keda":
                axes[0].axvline(tm, color=COLOR[c], lw=0.7, ls=":", alpha=0.7, zorder=2)

    subtitle = "autoscaler behavior: who scales which layer"
    if cap is not None:
        subtitle += f" (windowed to {cap/60:g} min)"
    fig.suptitle(f"G1 (REAL runs, n=1) — {subtitle}",
                 y=1.02, fontsize=11, fontweight="bold")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "figures", "G1_real_autoscaler_behavior.png")
    fig.savefig(out, dpi=300, bbox_inches="tight")
    print(f"wrote {out}")
    # print the numeric summary too
    print("\ncondition    pods(start→end)  workers(range)  executors(range)  rebalances")
    for c in CONDS:
        tp, vp = _series(c, "supervisor_pods", cap=cap)
        tw, vw = _series(c, "workers_total", cap=cap)
        te, ve = _series(c, "executors_total", cap=cap)
        rb = _rebalances(c, cap=cap)
        pods = f"{int(vp[0])}→{int(vp[-1])}" if vp else "n/a"
        wk = f"{int(min(vw))}-{int(max(vw))}" if vw else "n/a"
        ex = f"{int(min(ve))}-{int(max(ve))}" if ve else "n/a"
        layers = "+".join(sorted({l for _, l, _ in rb})) or "-"
        print(f"{c:12s} {pods:14s}  {wk:14s}  {ex:16s}  {len(rb)} ({layers})")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--window-cap", default=None,
                    help="Seconds to truncate every condition's series to before "
                         "comparing/plotting, so a condition that ran/settled longer "
                         "(e.g. dynamix) doesn't skew the comparison. Pass a number, "
                         "or 'auto' to cap at the shortest condition's max t_s. "
                         "Omit for no cap (raw full range per condition).")
    args = p.parse_args()
    cap = resolve_window_cap(args.window_cap)
    render(cap=cap)


if __name__ == "__main__":
    main()
