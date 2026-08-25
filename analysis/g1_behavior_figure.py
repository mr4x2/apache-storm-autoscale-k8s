#!/usr/bin/env python3
"""
g1_behavior_figure.py — G1 autoscaler-behavior figure: static vs. ARiSto-only vs.
DynamiX, windowed to the common 1800s comparison range.

Deliberately NOT a throughput/latency figure: those metrics currently collapse to
zero for extended stretches in every condition (real, unresolved issue — see
throughput-zero-blocker memory), so any mean/summary computed from them right now
would misrepresent the system. This figure instead plots what IS clean and real in
the current capture: Supervisor pod count (KEDA/infra layer), Storm worker count,
and executor count (ARiSto/topology layer) over time.

Run selection (picked after auditing every available run for single-session
integrity — see chat log 2026-08-08):
  - static:      timeseries_G1-static-r3.csv       (no autoscaler; fixed by protocol)
  - aristo_only: state_G1-aristo_only-r3.csv        (single clean session, n=6 rebalances)
  - dynamix:     state_G1-dynamix-r3.csv            (single clean session, n=16
                  rebalances; r1/r2 are multi-session-concatenated and excluded)

NORMALIZATION (added 2026-08-08): workers_total and executors_total are shown as
a running maximum, not raw readings. rulebase/v1/FlowCheck.java only ever
increments workers (`++workers`) and bolt executors (`+1`) -- there is no
decrement path -- so any observed decrease in these two series within a single
run is provably not an ARiSto decision (most likely a Storm worker-process
crash/restart blip), regardless of how the poller's heuristic labeled it in the
rebalance CSV. supervisor_pods is plotted as measured, unmodified: KEDA's
ScaledObject has a genuine active scale-down policy, so real decreases there are
plausible.

KNOWN CAVEAT (not fixed by this script): aristo_only's measured supervisor_pods
stays at 1 throughout, not the protocol-fixed 3 (`kubectl scale statefulset
supervisor --replicas=3` in docs/runbook-G1.md). Plotted as measured; protocol
target shown as a dashed reference line. Verify the scale step was actually applied
for that run before citing this figure.

Usage:
    scripts/venv/bin/python3 analysis/g1_behavior_figure.py
"""
from __future__ import annotations
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import figstyle

figstyle.apply_figure_style(frame="open")

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "scripts", "docs", "experiment-results", "G1")
WINDOW_CAP_S = 1800  # common comparison window (static's full duration)

# Validated categorical palette (dataviz skill, documented default, slots 1-3;
# passes all 6 checks incl. --pairs all, since these are step lines that can
# sit adjacent anywhere): blue / orange / teal-green.
COLOR = {"static": "#2a78d6", "aristo_only": "#eb6834", "dynamix": "#1baf7a"}
LABEL = {"static": "Static", "aristo_only": "ARiSto-only", "dynamix": "DynamiX"}
RUN = {"static": "r3", "aristo_only": "r3", "dynamix": "r3"}
PROTOCOL_FIXED_PODS = 3  # docs/runbook-G1.md: static & aristo_only hold Supervisor replicas fixed


def _rows(cond, kind):
    run = RUN[cond]
    if kind == "state":
        f = os.path.join(ROOT, cond, f"state_G1-{cond}-{run}.csv")
        if not os.path.isfile(f):
            f = os.path.join(ROOT, cond, f"timeseries_G1-{cond}-{run}.csv")
    else:
        f = os.path.join(ROOT, cond, f"timeseries_G1-{cond}-{run}.csv")
    if not os.path.isfile(f):
        return []
    return list(csv.DictReader(open(f)))


# rulebase/v1/FlowCheck.java only ever increments workers (`++workers`) and bolt
# executors (`+1`) -- there is no decrement path. Any observed DECREASE in these
# two series within a single run is therefore provably not an ARiSto decision
# (confirmed against FlowCheck.java + the user, 2026-08-08), regardless of how the
# poller's from_count/to_count heuristic labeled it in the rebalance CSV. Most
# likely cause: a Storm worker process crash/restart blip. Normalized to a running
# maximum so the chart shows ARiSto's real (monotonic, increment-only) actions.
# supervisor_pods is NOT normalized this way: KEDA's ScaledObject has a genuine
# active scale-down policy, so real decreases there are plausible and kept as-is.
MONOTONIC_COLS = {"workers_total", "executors_total"}


def _series(cond, col, cap=WINDOW_CAP_S):
    t, v = [], []
    for r in _rows(cond, "state"):
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
    if col in MONOTONIC_COLS and v:
        running_max = v[0]
        for i, x in enumerate(v):
            running_max = max(running_max, x)
            v[i] = running_max
    return t, v


def render():
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.6), sharex=True)
    specs = [
        ("supervisor_pods", "Supervisor pods\n(infrastructure layer / KEDA)"),
        ("workers_total", "Storm workers\n(topology layer / ARiSto)"),
        ("executors_total", "Executors\n(topology layer / ARiSto)"),
    ]
    conds = ["static", "aristo_only", "dynamix"]

    for ax, (col, title) in zip(axes, specs):
        for c in conds:
            t, v = _series(c, col)
            if not t:
                continue
            ax.step(t, v, where="post", color=COLOR[c], lw=1.8,
                    label=LABEL[c], zorder=3, solid_capstyle="round")
        if col == "supervisor_pods":
            xmax = WINDOW_CAP_S / 60.0
            ax.plot([0, xmax], [PROTOCOL_FIXED_PODS] * 2, color=COLOR["static"],
                     lw=1.2, ls=(0, (4, 2)), alpha=0.6, zorder=2,
                     label="Static\n(fixed by protocol; not telemetered)")
        ax.set_title(title, loc="left", fontsize=9)
        ax.set_xlabel("Time (min)")
        ax.margins(y=0.18)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        figstyle.set_frame(ax, "open")

    axes[0].set_ylabel("count")
    axes[0].legend(frameon=False, fontsize=6.3, loc="upper left")
    for i, letter in enumerate("abc"):
        figstyle.panel_letter(axes[i], letter)

    fig.suptitle("G1 — autoscaler behavior by condition (0–30 min, n = 1 representative run/condition)\n"
                  "workers/executors shown as running-maximum: ARiSto has no scale-down path, so observed decreases are artifacts",
                  y=1.10, fontsize=9.5, fontweight="bold")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "figures", "G1_behavior_static_aristo_dynamix.png")
    fig.savefig(out, dpi=300, bbox_inches="tight")
    print(f"wrote {out}")

    print("\ncondition    run  pods(start->end)  workers(range)  executors(range)")
    for c in conds:
        tp, vp = _series(c, "supervisor_pods")
        tw, vw = _series(c, "workers_total")
        te, ve = _series(c, "executors_total")
        pods = f"{int(vp[0])}->{int(vp[-1])}" if vp else "n/a (fixed=3, not telemetered)"
        wk = f"{int(min(vw))}-{int(max(vw))}" if vw else "n/a"
        ex = f"{int(min(ve))}-{int(max(ve))}" if ve else "n/a"
        print(f"{c:12s} {RUN[c]:4s} {pods:22s} {wk:14s}  {ex}")


if __name__ == "__main__":
    render()
