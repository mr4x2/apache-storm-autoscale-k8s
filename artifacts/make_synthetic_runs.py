"""
make_synthetic_runs.py — SYNTHETIC placeholder data generator for the DynamiX
experiments. **Every value produced here is fabricated** to exercise the
analysis + plotting pipeline before real cluster logs exist. It encodes only
qualitative expectations (DynamiX recovers fastest/steadiest; Static saturates;
single-layer arms are intermediate) so the figures render and the summary tables
populate. DELETE this data and replace with real exported runs before writing
any numbers into the paper.

Emits, under <outdir>/ :
    run_metadata.csv, timeseries_<run_id>.csv, rebalance_<run_id>.csv
conforming to metrics_schema.json.
"""
from __future__ import annotations
import os, json, argparse
import numpy as np
import pandas as pd

SCHEMA = "metrics_schema.json"
SEED = 20240601
PERIOD = 15  # s, matches schema sample_period_s

def _schema():
    with open(SCHEMA) as f: return json.load(f)

def _steps(sch):
    st, t0 = [], 0
    for s in sch["load_profile_default"]["steps"]:
        st.append((s["level"], s["offered_load_msgs_per_s"], t0, t0+s["duration_s"])); t0 += s["duration_s"]
    return st, t0

# per-condition qualitative behaviour knobs (SYNTHETIC)
#   cap_frac  : fraction of offered load it can sustain at steady state per level
#   tau_s     : settling time constant after a load step (s); larger = slower
#   noise     : steady-state relative noise (drives CoV)
#   lat_base  : base latency (ms) and lat_gain: latency growth as it saturates
COND = {
    "static":      dict(cap=[1.00, 0.62, 0.42], tau=90,  noise=0.05, lat_base=40, lat_gain=6.0, aristo=False, keda=False),
    "keda_only":   dict(cap=[1.00, 0.90, 0.74], tau=210, noise=0.09, lat_base=45, lat_gain=2.2, aristo=False, keda=True),
    "aristo_only": dict(cap=[1.00, 0.93, 0.80], tau=170, noise=0.07, lat_base=42, lat_gain=1.8, aristo=True,  keda=False),
    "dynamix":     dict(cap=[1.00, 0.98, 0.95], tau=110, noise=0.04, lat_base=38, lat_gain=1.0, aristo=True,  keda=True),
}

def _series_for(rng, steps, beh):
    """Build one timeseries (per-sample) for a condition behaviour dict."""
    rows = []
    prev_ss = None
    pods = 2; execs = 12          # initial
    pod_events, exec_events = [], []
    for lvl, offered, t0, t1 in steps:
        ss = beh["cap"][lvl-1] * offered            # steady-state acked target
        # scaling reactions (SYNTHETIC): more load -> arm grows resources if enabled
        if beh["keda"] and lvl >= 2:
            new_pods = min(2 + lvl, 6)
            if new_pods > pods: pod_events.append((t0 + int(0.25*(t1-t0)), pods, new_pods)); pods = new_pods
        if beh["aristo"] and lvl >= 2:
            new_ex = min(12 + 8*(lvl-1), 40)
            if new_ex > execs: exec_events.append((t0 + int(0.20*(t1-t0)), execs, new_ex)); execs = new_ex
        for t in range(t0, t1, PERIOD):
            frac = (t - t0)
            if prev_ss is None: prev_ss = ss
            # exponential approach from prev_ss to ss
            val = ss + (prev_ss - ss) * np.exp(-frac / beh["tau"])
            val *= (1 + rng.normal(0, beh["noise"]))
            val = max(val, 0)
            # latency rises with utilisation (offered/served gap)
            util = min(offered / max(val, 1), 3.0)
            lat = beh["lat_base"] * (1 + beh["lat_gain"] * max(util-1, 0)) * (1 + rng.normal(0, 0.05))
            cap_bolt = min(0.4 + 0.25*(lvl-1) + rng.normal(0,0.03), 1.2)
            wr = min(0.3 + 0.22*(lvl-1), 1.0)
            wscale = 0.6*wr + 0.2*min(cap_bolt,1.0) + 0.2*min(lat/200,1.0)
            rows.append(dict(t_s=t, offered_load_msgs_per_s=float(offered),
                             throughput_acked_per_s=round(val,1),
                             emitted_per_s=round(val*1.03,1),
                             complete_latency_ms=round(max(lat,1),1),
                             capacity_max_bolt=round(max(cap_bolt,0),3),
                             executors_total=int(execs), workers_total=int(max(2,execs//6)),
                             supervisor_pods=int(pods),
                             weight_scale=round(wscale,3),
                             cpu_util_ratio=round(min(0.3+0.2*(lvl-1)+rng.normal(0,0.03),1.0),3)))
        prev_ss = ss
    return pd.DataFrame(rows), pod_events, exec_events

def _emit_run(outdir, run_id, group, condition, beh, sch, rng, params, meta_rows):
    steps, total = _steps(sch)
    ts, pod_events, exec_events = _series_for(rng, steps, beh)
    ts.insert(0, "group", group); ts.insert(0, "condition", condition); ts.insert(0, "run_id", run_id)
    # order columns per schema
    tcols = [c["name"] for c in sch["files"]["timeseries"]["columns"]]
    ts = ts[tcols]
    ts.to_csv(os.path.join(outdir, f"timeseries_{run_id}.csv"), index=False)
    # rebalance events
    rb = []
    for (t, a, b) in exec_events:
        rb.append(dict(run_id=run_id, condition=condition, group=group, t_s=t, layer="aristo",
                       action="scale_out", component="parse_bolt", from_count=a, to_count=b,
                       trigger_value=0.82))
    for (t, a, b) in pod_events:
        rb.append(dict(run_id=run_id, condition=condition, group=group, t_s=t, layer="keda",
                       action="scale_out", component="supervisor", from_count=a, to_count=b,
                       trigger_value=0.80))
    rcols = [c["name"] for c in sch["files"]["rebalance_events"]["columns"]]
    pd.DataFrame(rb, columns=rcols).to_csv(os.path.join(outdir, f"rebalance_{run_id}.csv"), index=False)
    # metadata
    meta_rows.append(dict(run_id=run_id, group=group, condition=condition,
                          replicate=params.get("replicate",1),
                          params_json=json.dumps(params.get("params",{})),
                          load_profile=sch["load_profile_default"]["name"],
                          warmup_s=sch["load_profile_default"]["warmup_discard_s"],
                          cluster_spec=json.dumps({"nodes":3,"vcpu":4,"ram_gb":8,"k8s":"1.28","storm":"2.5"}),
                          aristo_jar=params.get("aristo_jar","storm-autoscale-v1-1.0.jar"),
                          start_iso="2024-06-01T00:00:00Z", end_iso="2024-06-01T00:30:00Z",
                          notes="SYNTHETIC placeholder"))

def _dynamix_variant(base, window_s=600, wscale=0.75, bolt=0.70):
    """Derive a synthetic DynamiX behaviour perturbed by G3 knob values, so the
    sensitivity plot shows a plausible stability/churn trade-off."""
    b = dict(COND["dynamix"])
    # smaller window / lower threshold -> more reactive: faster tau but noisier + more rebalances
    b["tau"]   = float(np.interp(window_s, [300,600,900,1200], [80,110,150,200]))
    b["noise"] = float(np.interp(window_s, [300,600,900,1200], [0.075,0.04,0.045,0.06]))
    # threshold effects folded into noise/cap slightly
    b["noise"] *= float(np.interp(wscale, [0.65,0.75,0.85], [1.15,1.0,1.12]))
    b["_reb_scale"] = float(np.interp(window_s,[300,600,900,1200],[1.6,1.0,0.7,0.55])) * \
                      float(np.interp(wscale,[0.65,0.75,0.85],[1.4,1.0,0.75])) * \
                      float(np.interp(bolt,[0.6,0.7,0.8],[1.3,1.0,0.8]))
    return b

def main(outdir="data"):
    os.makedirs(outdir, exist_ok=True)
    sch = _schema(); rng = np.random.default_rng(SEED); meta = []

    # ---- Group 1: 4 conditions x 3 replicates ----
    for cond in ["static","keda_only","aristo_only","dynamix"]:
        for r in (1,2,3):
            jar = "none" if not COND[cond]["aristo"] else "storm-autoscale-v1-1.0.jar"
            _emit_run(outdir, f"G1-{cond}-r{r}", "G1", cond, COND[cond], sch, rng,
                      {"replicate":r,"aristo_jar":jar,
                       "params":{"window_s":600,"wscale_threshold":0.75,"bolt_cap_threshold":0.70,
                                 "keda_enabled":COND[cond]["keda"],"cooldown_s":300}}, meta)

    # ---- Group 2: original vs modified ARiSto v1 (KEDA off) ----
    # modified = aristo_only behaviour; original under-scales at high load (low cap, weak signal)
    orig = dict(COND["aristo_only"]); orig["cap"] = [1.00, 0.70, 0.48]; orig["tau"] = 260; orig["noise"]=0.10
    for cond, beh, jar in [("aristo_orig_v1", orig, "storm-autoscale-aristo-1.0.jar"),
                            ("aristo_mod_v1", COND["aristo_only"], "storm-autoscale-v1-1.0.jar")]:
        for r in (1,2,3):
            df_beh = dict(beh)
            _emit_run(outdir, f"G2-{cond}-r{r}", "G2", cond, df_beh, sch, rng,
                      {"replicate":r,"aristo_jar":jar,
                       "params":{"window_s":600,"wscale_threshold":0.75,"bolt_cap_threshold":0.70,
                                 "keda_enabled":False,"cooldown_s":300}}, meta)
    # For G2, weaken the original's scaler signal so F5 shows the "collapse toward 0"
    for r in (1,2,3):
        p = os.path.join(outdir, f"timeseries_G2-aristo_orig_v1-r{r}.csv")
        d = pd.read_csv(p)
        # cumulative-average artefact: signal decays across the run
        d["weight_scale"] = (d["weight_scale"] * np.exp(-d["t_s"]/900.0)).round(3)
        d.to_csv(p, index=False)

    # ---- Group 3: OFAT sweeps + shared baseline ----
    def emit_g3(cond_label, window_s, wscale, bolt, meta):
        beh = _dynamix_variant(COND["dynamix"], window_s, wscale, bolt)
        reb_scale = beh.pop("_reb_scale", 1.0)
        for r in (1,2,3):
            rid = f"G3-{cond_label}-r{r}"
            _emit_run(outdir, rid, "G3", cond_label, beh, sch, rng,
                      {"replicate":r,"aristo_jar":"storm-autoscale-v1-1.0.jar",
                       "params":{"window_s":window_s,"wscale_threshold":wscale,"bolt_cap_threshold":bolt,
                                 "keda_enabled":True,"cooldown_s":300}}, meta)
            # scale rebalance frequency by reb_scale (duplicate/prune events)
            rp = os.path.join(outdir, f"rebalance_{rid}.csv"); rdf = pd.read_csv(rp)
            if reb_scale > 1.15 and len(rdf):
                extra = rdf.copy(); extra["t_s"] = extra["t_s"] + 120
                rdf = pd.concat([rdf, extra.iloc[:max(1,int((reb_scale-1)*len(rdf)))]], ignore_index=True)
            elif reb_scale < 0.85 and len(rdf) > 1:
                rdf = rdf.iloc[:max(1,int(reb_scale*len(rdf)))]
            rdf.to_csv(rp, index=False)

    emit_g3("baseline", 600, 0.75, 0.70, meta)
    for w in (300, 900, 1200):            emit_g3(f"window_s={w}", w, 0.75, 0.70, meta)
    for th in (0.65, 0.85):               emit_g3(f"wscale_threshold={th}", 600, th, 0.70, meta)
    for bc in (0.6, 0.8):                 emit_g3(f"bolt_cap_threshold={bc}", 600, 0.75, bc, meta)

    # metadata
    mcols = [c["name"] for c in sch["files"]["run_metadata"]["columns"]]
    pd.DataFrame(meta)[mcols].to_csv(os.path.join(outdir, "run_metadata.csv"), index=False)
    print(f"SYNTHETIC data written to {outdir}/: {len(meta)} runs")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="data")
    main(ap.parse_args().outdir)
