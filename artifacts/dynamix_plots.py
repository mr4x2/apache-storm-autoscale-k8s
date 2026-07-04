"""
dynamix_plots.py — publication figures for the DynamiX experiments (Section V).

Consumes a Campaign from dynamix_analysis.py (which validates the CSVs against
metrics_schema.json). Produces F1-F6 as 300-dpi PNGs with English-only labels.
Uses figstyle.apply_figure_style() (ported from the figure-style skill) for
publication-grade rcParams.

Usage
-----
    import dynamix_analysis as da, dynamix_plots as dp
    camp = da.load_campaign("data")
    dp.render_all(camp, outdir="figures")
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # find figstyle/dynamix_analysis regardless of cwd
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

import figstyle
import dynamix_analysis as da

figstyle.apply_figure_style(frame="open")

# stable colour + order mapping for the 4 conditions (colour threads across figs)
COND_COLORS = {
    "static":      "#9e9e9e",   # grey  = no elasticity
    "keda_only":   "#4c78a8",   # blue  = infra only
    "aristo_only": "#f58518",   # orange= topology only
    "dynamix":     "#54a24b",   # green = full system (focal)
}
COND_LABEL = {"static":"Static", "keda_only":"KEDA-only",
              "aristo_only":"ARiSto-only", "dynamix":"DynamiX"}
COND_ORDER = ["static", "keda_only", "aristo_only", "dynamix"]

def _load_step_shading(ax, camp, y=None):
    steps = da.load_steps(camp.schema)
    for _, s in steps.iterrows():
        if int(s.level) % 2 == 0:
            ax.axvspan(s.t_start/60, s.t_end/60, color="#000000", alpha=0.04, lw=0, zorder=0)
        ax.axvline(s.t_start/60, color=figstyle.META_GREY, lw=0.5, ls=":", zorder=1)
        ax.text(((s.t_start+s.t_end)/2)/60, ax.get_ylim()[1] if y is None else y,
                f"{int(s.offered_load_msgs_per_s/1000)}k msg/s",
                ha="center", va="top", fontsize=6, color=figstyle.META_GREY)

def _mean_trace(camp, group, condition, col):
    """Mean across replicates on the common t_s grid."""
    d = camp.ts(group=group, condition=condition)
    if d.empty: return None, None, None
    piv = d.pivot_table(index="t_s", columns="run_id", values=col, aggfunc="mean")
    t = piv.index.to_numpy()/60.0  # minutes
    m = piv.mean(axis=1).to_numpy()
    sd = piv.std(axis=1).to_numpy() if piv.shape[1] > 1 else np.zeros_like(m)
    return t, m, sd

# --------------------------------------------------------------------------- #
# F1 — throughput vs time, 4 conditions overlaid
# --------------------------------------------------------------------------- #
def fig_throughput_timeseries(camp, path="figures/F1_throughput_timeseries.png"):
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    for cond in COND_ORDER:
        t, m, sd = _mean_trace(camp, "G1", cond, "throughput_acked_per_s")
        if t is None: continue
        lw = 1.8 if cond == "dynamix" else 1.1
        ax.plot(t, m, color=COND_COLORS[cond], lw=lw, label=COND_LABEL[cond], zorder=3)
        if np.any(sd > 0):
            ax.fill_between(t, m-sd, m+sd, color=COND_COLORS[cond], alpha=0.12, lw=0, zorder=2)
    # offered load reference
    t, off, _ = _mean_trace(camp, "G1", "dynamix", "offered_load_msgs_per_s")
    if t is not None:
        ax.plot(t, off, color="black", lw=0.8, ls="--", label="Offered load", zorder=4)
    ax.set_xlabel("Time (min)"); ax.set_ylabel("Acked throughput (tuple/s)")
    ax.set_title("DynamiX sustains throughput closest to offered load across the ramp")
    _load_step_shading(ax, camp)
    ax.legend(loc="upper left", ncol=2)
    fig.savefig(path); plt.close(fig); return path

# --------------------------------------------------------------------------- #
# F2 — latency: p95 bar + CDF
# --------------------------------------------------------------------------- #
def fig_latency(camp, path="figures/F2_latency.png"):
    fig, (axb, axc) = plt.subplots(1, 2, figsize=(6.8, 3.2))
    plm = da.per_level_metrics(camp); plm = plm[plm["group"] == "G1"]
    top = plm["level"].max()
    top_lvl = plm[plm["level"] == top]
    conds = [c for c in COND_ORDER if c in top_lvl["condition"].unique()]
    xs = np.arange(len(conds))
    vals = [top_lvl[top_lvl["condition"] == c]["latency_p95"].mean() for c in conds]
    cols = [COND_COLORS[c] for c in conds]
    axb.bar(xs, vals, color=cols, width=0.62)
    axb.set_xticks(xs); axb.set_xticklabels([COND_LABEL[c] for c in conds], rotation=20, ha="right")
    axb.set_ylabel("p95 complete latency (ms)")
    axb.set_title(f"p95 latency at {int(top_lvl['offered_load_msgs_per_s'].iloc[0]/1000)}k msg/s")
    # CDF at top load
    for cond in conds:
        d = camp.ts(group="G1", condition=cond)
        steps = da.load_steps(camp.schema); s = steps[steps.level == top].iloc[0]
        seg = d[(d["t_s"] >= s.t_start) & (d["t_s"] < s.t_end)]["complete_latency_ms"].dropna().to_numpy()
        if len(seg) == 0: continue
        xs_c = np.sort(seg); ys_c = np.arange(1, len(xs_c)+1)/len(xs_c)
        axc.plot(xs_c, ys_c, color=COND_COLORS[cond], lw=1.4, label=COND_LABEL[cond])
    axc.set_xlabel("Complete latency (ms)"); axc.set_ylabel("CDF")
    axc.set_title("Latency distribution at peak load"); axc.legend(loc="lower right")
    figstyle.panel_letter(axb, "a"); figstyle.panel_letter(axc, "b")
    fig.tight_layout(); fig.savefig(path); plt.close(fig); return path

# --------------------------------------------------------------------------- #
# F3 — resource trajectories (pods + executors)
# --------------------------------------------------------------------------- #
def fig_resources(camp, path="figures/F3_resources.png"):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6.4, 4.6), sharex=True)
    for cond in COND_ORDER:
        t, pods, _ = _mean_trace(camp, "G1", cond, "supervisor_pods")
        if t is not None and np.any(~np.isnan(pods)):
            ax1.step(t, pods, where="post", color=COND_COLORS[cond], lw=1.4, label=COND_LABEL[cond])
        t, ex, _ = _mean_trace(camp, "G1", cond, "executors_total")
        if t is not None and np.any(~np.isnan(ex)):
            ax2.step(t, ex, where="post", color=COND_COLORS[cond], lw=1.4, label=COND_LABEL[cond])
    ax1.set_ylabel("Supervisor pods"); ax1.set_title("Infrastructure scaling (KEDA)")
    ax2.set_ylabel("Total executors"); ax2.set_xlabel("Time (min)")
    ax2.set_title("Topology scaling (ARiSto)")
    _load_step_shading(ax1, camp); _load_step_shading(ax2, camp)
    ax1.legend(loc="upper left", ncol=2, fontsize=6)
    figstyle.panel_letter(ax1, "a"); figstyle.panel_letter(ax2, "b")
    fig.tight_layout(); fig.savefig(path); plt.close(fig); return path

# --------------------------------------------------------------------------- #
# F4 — settling time & rebalance count, grouped bars
# --------------------------------------------------------------------------- #
def fig_settling_rebalance(camp, path="figures/F4_settling_rebalance.png"):
    fig, (axs, axr) = plt.subplots(1, 2, figsize=(6.8, 3.2))
    # settling time at the highest load step, per condition
    plm_runs = camp.timeseries["run_id"].unique()
    settle = pd.concat([da.settling_time(camp, r) for r in plm_runs], ignore_index=True)
    settle = settle.merge(camp.metadata[["run_id","condition","group"]], on="run_id", how="left")
    settle = settle[settle["group"] == "G1"]
    top = settle["level"].max()
    conds = [c for c in COND_ORDER if c in settle["condition"].unique()]
    xs = np.arange(len(conds))
    means = [settle[(settle.condition==c)&(settle.level==top)]["settling_time_s"].mean() for c in conds]
    # censored (never settled) -> hatched bar at axis cap
    cap = np.nanmax([m for m in means if not np.isnan(m)] + [1]) * 1.25
    for i, (c, m) in enumerate(zip(conds, means)):
        if np.isnan(m):
            axs.bar(i, cap, color="none", edgecolor=COND_COLORS[c], hatch="///", lw=1.0)
            axs.text(i, cap, "no settle", ha="center", va="bottom", fontsize=6, color=COND_COLORS[c])
        else:
            axs.bar(i, m, color=COND_COLORS[c], width=0.62)
    axs.set_xticks(xs); axs.set_xticklabels([COND_LABEL[c] for c in conds], rotation=20, ha="right")
    axs.set_ylabel("Settling time at peak load (s)")
    axs.set_title("Time to re-stabilise after the 8k step")
    # rebalance counts stacked (aristo vs keda)
    rc = da.rebalance_counts(camp); rc = rc[rc["group"]=="G1"]
    agg = rc.groupby("condition")[["aristo_scale_out","aristo_scale_in","keda_scale_out","keda_scale_in"]].mean()
    conds2 = [c for c in COND_ORDER if c in agg.index]
    xs2 = np.arange(len(conds2))
    aristo = (agg.loc[conds2,"aristo_scale_out"]+agg.loc[conds2,"aristo_scale_in"]).to_numpy()
    keda   = (agg.loc[conds2,"keda_scale_out"]+agg.loc[conds2,"keda_scale_in"]).to_numpy()
    axr.bar(xs2, aristo, width=0.62, color="#f58518", label="ARiSto (topology)")
    axr.bar(xs2, keda, width=0.62, bottom=aristo, color="#4c78a8", label="KEDA (infra)")
    axr.set_xticks(xs2); axr.set_xticklabels([COND_LABEL[c] for c in conds2], rotation=20, ha="right")
    axr.set_ylabel("Scaling actions per run"); axr.set_title("Rebalance activity by layer")
    axr.legend(loc="upper left", fontsize=6)
    figstyle.panel_letter(axs, "a"); figstyle.panel_letter(axr, "b")
    fig.tight_layout(); fig.savefig(path); plt.close(fig); return path

# --------------------------------------------------------------------------- #
# F5 — Group 2: modified vs original ARiSto throughput
# --------------------------------------------------------------------------- #
def fig_group2(camp, path="figures/F5_group2_formula.png"):
    g2 = camp.ts(group="G2")
    if g2.empty:
        return None
    fig, (axsig, axact) = plt.subplots(2, 1, figsize=(6.4, 4.6), sharex=True)
    g2cols = {"aristo_orig_v1":"#d62728", "aristo_mod_v1":"#54a24b"}
    g2lab  = {"aristo_orig_v1":"Original v1 (cumulative avg)", "aristo_mod_v1":"Modified v1 (600 s window)"}
    for cond, col in g2cols.items():
        # scaler-computed signal (weight_scale as proxy for the throughput signal it sees)
        t, sig, _ = _mean_trace(camp, "G2", cond, "weight_scale")
        if t is not None:
            axsig.plot(t, sig, color=col, lw=1.5, label=g2lab[cond])
        t, act, _ = _mean_trace(camp, "G2", cond, "throughput_acked_per_s")
        if t is not None:
            axact.plot(t, act, color=col, lw=1.5, label=g2lab[cond])
    axsig.set_ylabel("Scaler trigger signal"); axsig.set_title("Scaler-computed signal: original formula collapses toward 0")
    axact.set_ylabel("Acked throughput (tuple/s)"); axact.set_xlabel("Time (min)")
    axact.set_title("Resulting actual throughput")
    _load_step_shading(axsig, camp); _load_step_shading(axact, camp)
    axsig.legend(loc="upper left", fontsize=6)
    figstyle.panel_letter(axsig, "a"); figstyle.panel_letter(axact, "b")
    fig.tight_layout(); fig.savefig(path); plt.close(fig); return path

# --------------------------------------------------------------------------- #
# F6 — Group 3: parameter sensitivity
# --------------------------------------------------------------------------- #
def fig_group3(camp, path="figures/F6_sensitivity.png"):
    g3 = da.summarize_group3(camp)
    if g3.empty:
        return None
    knobs = ["window_s", "wscale_threshold", "bolt_cap_threshold"]
    klab  = {"window_s":"Observation window (s)", "wscale_threshold":"weight_scale threshold",
             "bolt_cap_threshold":"Bolt-capacity threshold"}
    kbase = {"window_s":600, "wscale_threshold":0.75, "bolt_cap_threshold":0.70}
    fig, axes = plt.subplots(1, 3, figsize=(8.4, 3.0))
    for ax, knob in zip(axes, knobs):
        sub = g3[g3["knob"] == knob].sort_values("knob_val")
        if sub.empty: continue
        x = sub["knob_val"].to_numpy()
        cov = sub["throughput_cov_mean"].to_numpy()
        reb = sub["rebalance_freq_mean"].to_numpy()
        ax.plot(x, cov, "-o", color="#54a24b", lw=1.4, ms=4, label="Throughput CoV")
        ax.set_xlabel(klab[knob]); ax.set_ylabel("Throughput CoV (lower=stabler)", color="#54a24b")
        ax.tick_params(axis="y", labelcolor="#54a24b")
        ax2 = ax.twinx()
        ax2.plot(x, reb, "-s", color="#4c78a8", lw=1.4, ms=4, label="Rebalance freq")
        ax2.set_ylabel("Rebalances/run", color="#4c78a8"); ax2.tick_params(axis="y", labelcolor="#4c78a8")
        ax2.spines["right"].set_visible(True)
        if kbase[knob] in list(x):
            ax.axvline(kbase[knob], color=figstyle.META_GREY, ls=":", lw=0.8)
            ax.text(kbase[knob], ax.get_ylim()[1], " baseline", fontsize=6, color=figstyle.META_GREY, va="top")
    fig.suptitle("Parameter sensitivity: stability vs rebalance churn (peak load)", x=0.02, ha="left")
    fig.tight_layout(); fig.savefig(path); plt.close(fig); return path

# --------------------------------------------------------------------------- #
def render_all(camp, outdir="figures"):
    os.makedirs(outdir, exist_ok=True)
    made = {}
    for name, fn in [("F1", fig_throughput_timeseries), ("F2", fig_latency),
                     ("F3", fig_resources), ("F4", fig_settling_rebalance),
                     ("F5", fig_group2), ("F6", fig_group3)]:
        default = {"F1":"F1_throughput_timeseries.png","F2":"F2_latency.png",
                   "F3":"F3_resources.png","F4":"F4_settling_rebalance.png",
                   "F5":"F5_group2_formula.png","F6":"F6_sensitivity.png"}[name]
        try:
            p = fn(camp, os.path.join(outdir, default))
            made[name] = p
        except Exception as e:
            made[name] = f"ERROR: {e}"
    return made

if __name__ == "__main__":
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else "data"
    camp = da.load_campaign(d, sys.argv[2] if len(sys.argv) > 2 else "metrics_schema.json")
    print(render_all(camp))
