#!/usr/bin/env python3
"""
Export one experiment run from Prometheus into timeseries_<run_id>.csv.

Usage:
    python3 export_run.py \
        --run-id G1-static-r1 \
        --condition static \
        --group G1 \
        --replicate 1 \
        --start 1783267880 \
        --end   1783269680 \
        --prom  http://34.126.115.181:30003 \
        --out   docs/experiment-results/G1/static/

Requires: pip install requests pandas
"""
import argparse, csv, json, os, sys
from datetime import datetime, timezone
import requests
import pandas as pd

QUERIES = {
    "throughput_acked_per_s": 'sum(rate(spouts_acked{SpoutId="spout-data-iot-data"}[1m]))',
    "complete_latency_ms":    'spouts_complete_latency{SpoutId="spout-data-iot-data"}',
    "capacity_max_bolt":      'max(bolts_capacity{BoltId=~"^split-.*"})',
    "workers_total":          'worker_cluster_used{ClusterHost="nimbus-ui:8081"}',
    "weight_scale":           'weight_scale{ClusterHost="nimbus-ui:8081"}',
}

LOAD_STEPS = [
    (0,    600,  1000),
    (600,  1200, 4000),
    (1200, 1800, 8000),
]


def query_range(prom_url, query, start, end, step=15):
    resp = requests.get(
        f"{prom_url}/api/v1/query_range",
        params={"query": query, "start": start, "end": end, "step": f"{step}s"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data["status"] != "success":
        raise RuntimeError(f"Prometheus error: {data}")
    results = data["data"]["result"]
    if not results:
        return {}
    # take first result series
    return {int(ts): float(val) for ts, val in results[0]["values"]}


def offered_load(t_s):
    for t_start, t_end, load in LOAD_STEPS:
        if t_start <= t_s < t_end:
            return load
    return 8000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id",    required=True)
    ap.add_argument("--condition", required=True)
    ap.add_argument("--group",     required=True)
    ap.add_argument("--replicate", required=True, type=int)
    ap.add_argument("--start",     required=True, type=int, help="Unix epoch start")
    ap.add_argument("--end",       required=True, type=int, help="Unix epoch end")
    ap.add_argument("--prom",      default="http://34.126.115.181:30003")
    ap.add_argument("--out",       default=".")
    ap.add_argument("--step",      default=15, type=int)
    args = ap.parse_args()

    print(f"Exporting {args.run_id} [{args.start} → {args.end}] from {args.prom}")

    series = {}
    for col, q in QUERIES.items():
        print(f"  querying {col}...")
        series[col] = query_range(args.prom, q, args.start, args.end, args.step)

    # build unified timestamp list
    all_ts = sorted(set().union(*[set(v.keys()) for v in series.values()]))
    if not all_ts:
        print("ERROR: no data returned from Prometheus", file=sys.stderr)
        sys.exit(1)

    rows = []
    for ts in all_ts:
        t_s = ts - args.start
        rows.append({
            "run_id":                args.run_id,
            "condition":             args.condition,
            "group":                 args.group,
            "t_s":                   t_s,
            "offered_load_msgs_per_s": offered_load(t_s),
            "throughput_acked_per_s":  series["throughput_acked_per_s"].get(ts, ""),
            "emitted_per_s":           "",
            "complete_latency_ms":     series["complete_latency_ms"].get(ts, ""),
            "capacity_max_bolt":       series["capacity_max_bolt"].get(ts, ""),
            "executors_total":         "",
            "workers_total":           series["workers_total"].get(ts, ""),
            "supervisor_pods":         "",
            "weight_scale":            series["weight_scale"].get(ts, ""),
            "cpu_util_ratio":          "",
        })

    df = pd.DataFrame(rows)
    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, f"timeseries_{args.run_id}.csv")
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} rows → {out_path}")

    # print metadata row to append manually
    params = json.dumps({"window_s": 600, "wscale_threshold": 0.75,
                         "bolt_cap_threshold": 0.7, "keda_enabled": False,
                         "aristo_jar": "none", "cooldown_s": 300})
    start_iso = datetime.fromtimestamp(args.start, tz=timezone.utc).isoformat()
    end_iso   = datetime.fromtimestamp(args.end,   tz=timezone.utc).isoformat()
    meta = (f"{args.run_id},{args.group},{args.condition},{args.replicate},"
            f'"{params}",ramp_1k_4k_8k_10min,120,,none,{start_iso},{end_iso},')
    print(f"\nAppend to run_metadata.csv:\n{meta}")


if __name__ == "__main__":
    main()
