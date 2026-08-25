#!/usr/bin/env python3
"""
Convert a raw ARiSto OutputWriter log (`<topology>_aristo_rb.txt`) into a
schema-valid rebalance_<run_id>.csv that analysis/dynamix_analysis.py can load.

The raw log is written by rulebase/v1/OutputWriter (append-mode). Each line is a
whitespace-delimited snapshot of the topology configuration at one autoscaler
decision, e.g.:

    workers=2 sum-10=1 split-1=1 ... throughput=30.07 latency=NaN time_spent_sec=883

This script diffs each line against the previous one and emits ONE rebalance row
per component whose parallelism changed (plus a "workers" row when the worker
count changes). The first line is the baseline reference and produces no rows.

Output columns (docs/metrics-schema.json → files.rebalance):
    run_id, condition, group, t_s, layer, action, component,
    from_count, to_count, trigger_value

Usage:
    python3 rb_to_csv.py \
        --in    docs/experiment-results/G1/aristo_only/raw_rb_G1-aristo_only-r1.txt \
        --run-id    G1-aristo_only-r1 \
        --condition aristo_only \
        --group     G1 \
        --out       docs/experiment-results/G1/aristo_only/

t_s alignment:
    The raw `time_spent_sec` is seconds since the AUTOSCALER started, but the
    schema wants t_s = seconds since the LOAD DRIVER started (0-aligned, same
    origin as timeseries_<run_id>.csv). If you started the autoscaler N seconds
    after the load ramp began, pass --t-offset N (added to every t_s). If the
    autoscaler started N seconds BEFORE the load, pass a negative value.

Stdlib only — no pandas/requests needed.
"""
import argparse
import csv
import math
import os
import sys

RESERVED = {"throughput", "latency", "time_spent_sec"}
LAYER = "aristo"
HEADER = ["run_id", "condition", "group", "t_s", "layer", "action",
          "component", "from_count", "to_count", "trigger_value"]


def parse_line(line):
    """Parse one raw log line into (counts, meta).

    counts: {component_name -> int parallelism} including 'workers'.
    meta:   {'throughput': float|None, 'latency': float|None,
             'time_spent_sec': int|None, 'target_reached': bool}
    Returns (None, None) for blank lines.
    """
    line = line.strip()
    if not line:
        return None, None

    counts, meta = {}, {"throughput": None, "latency": None,
                        "time_spent_sec": None, "target_reached": False}

    if "target reached" in line:
        meta["target_reached"] = True
        line = line.replace("target reached", "")

    for tok in line.split():
        if "=" not in tok:
            continue
        key, val = tok.split("=", 1)
        if key == "throughput":
            meta["throughput"] = _to_float(val)
        elif key == "latency":
            meta["latency"] = _to_float(val)
        elif key == "time_spent_sec":
            meta["time_spent_sec"] = _to_int(val)
        else:
            c = _to_int(val)
            if c is not None:
                counts[key] = c
    return counts, meta


def _to_float(v):
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (ValueError, TypeError):
        return None


def _to_int(v):
    try:
        return int(v)
    except (ValueError, TypeError):
        try:
            return int(float(v))  # tolerate "2.0"
        except (ValueError, TypeError):
            return None


def convert(lines, run_id, condition, group, t_offset):
    rows = []
    prev_counts = None
    prev_t = 0
    line_no = 0

    for raw in lines:
        line_no += 1
        counts, meta = parse_line(raw)
        if counts is None:
            continue

        t_raw = meta["time_spent_sec"]
        t_s = (t_raw if t_raw is not None else prev_t) + t_offset
        trigger = meta["throughput"]

        # Detect append-mode concatenation of multiple runs: time_spent_sec
        # resets (goes backwards) when a new autoscaler process starts.
        if t_raw is not None and t_raw + t_offset < prev_t:
            print(f"WARNING: t_s went backwards at line {line_no} "
                  f"({t_raw}s < previous {prev_t - t_offset}s) — the raw file "
                  f"likely concatenates MULTIPLE runs. Split it per run first.",
                  file=sys.stderr)

        if prev_counts is not None:
            for comp in sorted(set(prev_counts) | set(counts)):
                frm = prev_counts.get(comp)
                to = counts.get(comp)
                if frm is None or to is None or frm == to:
                    continue
                action = "scale_out" if to > frm else "scale_in"
                rows.append({
                    "run_id": run_id, "condition": condition, "group": group,
                    "t_s": t_s, "layer": LAYER, "action": action,
                    "component": comp, "from_count": frm, "to_count": to,
                    "trigger_value": "" if trigger is None else round(trigger, 4),
                })

        prev_counts = counts
        if t_raw is not None:
            prev_t = t_raw + t_offset
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="infile", required=True,
                    help="raw <topology>_aristo_rb.txt copied out of the nimbus pod")
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--condition", required=True)
    ap.add_argument("--group", required=True)
    ap.add_argument("--out", default=".", help="output directory")
    ap.add_argument("--t-offset", type=int, default=0,
                    help="seconds added to every t_s to align autoscaler-start "
                         "to load-driver-start (default 0)")
    args = ap.parse_args()

    if not os.path.isfile(args.infile):
        print(f"ERROR: no such file: {args.infile}", file=sys.stderr)
        sys.exit(1)

    with open(args.infile) as f:
        lines = f.readlines()

    rows = convert(lines, args.run_id, args.condition, args.group, args.t_offset)

    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, f"rebalance_{args.run_id}.csv")
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        w.writerows(rows)

    print(f"Parsed {len(lines)} lines → {len(rows)} rebalance events → {out_path}")
    if not rows:
        print("Note: 0 rebalance events. Either no scaling happened, or the log "
              "has only one config snapshot (baseline). This is normal for a run "
              "that never triggered a scale action.", file=sys.stderr)


if __name__ == "__main__":
    main()
