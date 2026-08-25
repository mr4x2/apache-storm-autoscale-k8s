#!/usr/bin/env python3
"""
During-run state poller for a DynamiX experiment.

Polls, on a fixed interval, the two sources that Prometheus does NOT store:
  * Storm REST  (per-component + total executors, worker count, bolt capacity)
  * kubectl     (supervisor StatefulSet replica count = pod count)

and writes two files:
  * state_<run_id>.csv      — one row per tick (ground-truth topology state)
  * rebalance_<run_id>.csv  — schema-valid rebalance events, derived by diffing
                              consecutive state rows. Layer is inferred from the
                              dimension that changed:
                                executor/worker change -> layer=aristo
                                supervisor pod change  -> layer=keda

This replaces the lossy OutputWriter log as the authoritative rebalance source
and fills the executors_total / supervisor_pods columns that export_run.py
leaves blank. Run it in the BACKGROUND for the whole run (Storm REST + pod count
are instantaneous — they can't be back-queried after the fact).

Typical use (one run):
    # 1. start BEFORE load, t0 = load-start epoch (align with export_run --start)
    scripts/venv/bin/python3 scripts/storm_snapshot.py \
        --run-id G1-aristo_only-r1 --condition aristo_only --group G1 \
        --t0 $(date +%s) \
        --out docs/experiment-results/G1/aristo_only/ &
    SNAP_PID=$!
    # 2. run the ramp ...
    # 3. stop -> it finalizes rebalance_<run_id>.csv on SIGTERM/SIGINT
    kill $SNAP_PID

Recover a rebalance file from an existing state CSV (e.g. after kill -9):
    scripts/venv/bin/python3 scripts/storm_snapshot.py \
        --run-id G1-aristo_only-r1 --condition aristo_only --group G1 \
        --out docs/experiment-results/G1/aristo_only/ --finalize-only

Requires: requests (in scripts/venv), and `kubectl` on PATH.
"""
import argparse
import csv
import json
import os
import signal
import subprocess
import sys
import time

import requests

REB_HEADER = ["run_id", "condition", "group", "t_s", "layer", "action",
              "component", "from_count", "to_count", "trigger_value"]
STATE_HEADER = ["t_s", "epoch", "workers_total", "executors_total",
                "supervisor_pods", "capacity_max", "components_json"]

_stop = False


def _handle_stop(signum, frame):
    global _stop
    _stop = True


def find_topology_id(storm_url, name):
    r = requests.get(f"{storm_url}/api/v1/topology/summary", timeout=15)
    r.raise_for_status()
    tops = r.json().get("topologies", [])
    matches = [t for t in tops if t.get("name") == name]
    if not matches:
        if len(tops) == 1:
            return tops[0]["id"]
        raise RuntimeError(f"topology '{name}' not found; available: "
                           f"{[t.get('name') for t in tops]}")
    return matches[0]["id"]


def poll_state(storm_url, topo_id):
    """Return (workers_total, executors_total, capacity_max, {component: executors})."""
    r = requests.get(f"{storm_url}/api/v1/topology/{topo_id}",
                     params={"window": "600"}, timeout=15)
    r.raise_for_status()
    d = r.json()

    comps = {}
    caps = []
    for s in d.get("spouts", []):
        comps[s["spoutId"]] = _int(s.get("executors"))
    for b in d.get("bolts", []):
        comps[b["boltId"]] = _int(b.get("executors"))
        c = _float(b.get("capacity"))
        if c is not None:
            caps.append(c)

    workers = _int(d.get("workersTotal"))
    execs = _int(d.get("executorsTotal"))
    cap_max = max(caps) if caps else None
    return workers, execs, cap_max, comps


def poll_pods(namespace, sts):
    """Supervisor pod count via kubectl (readyReplicas, fallback replicas)."""
    try:
        out = subprocess.run(
            ["kubectl", "get", "statefulset", sts, "-n", namespace, "-o", "json"],
            capture_output=True, text=True, timeout=15, check=True).stdout
        st = json.loads(out).get("status", {})
        for k in ("readyReplicas", "currentReplicas", "replicas"):
            if st.get(k) is not None:
                return int(st[k])
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
            json.JSONDecodeError, ValueError) as e:
        print(f"  WARN kubectl pod poll failed: {e}", file=sys.stderr)
    return None


def _int(v):
    try:
        return int(v)
    except (ValueError, TypeError):
        try:
            return int(float(v))
        except (ValueError, TypeError):
            return None


def _float(v):
    try:
        f = float(v)
        return f if f == f else None  # drop NaN
    except (ValueError, TypeError):
        return None


def run_poller(args, state_path):
    topo_id = find_topology_id(args.storm_url, args.topology)
    print(f"Polling topology '{args.topology}' ({topo_id}) every {args.interval}s "
          f"→ {state_path}\n(Ctrl-C / SIGTERM to stop and finalize)")

    new_file = not os.path.exists(state_path) or os.path.getsize(state_path) == 0
    f = open(state_path, "a", newline="")
    w = csv.writer(f)
    if new_file:
        w.writerow(STATE_HEADER)
        f.flush()

    deadline = (args.t0 + args.duration) if args.duration else None
    while not _stop:
        now = time.time()
        if deadline and now >= deadline:
            print("Duration reached; stopping.")
            break
        t_s = int(round(now - args.t0))
        try:
            workers, execs, cap_max, comps = poll_state(args.storm_url, topo_id)
        except requests.RequestException as e:
            print(f"  WARN storm poll failed at t_s={t_s}: {e}", file=sys.stderr)
            time.sleep(args.interval)
            continue
        pods = poll_pods(args.namespace, args.sts)

        w.writerow([t_s, int(now),
                    "" if workers is None else workers,
                    "" if execs is None else execs,
                    "" if pods is None else pods,
                    "" if cap_max is None else round(cap_max, 4),
                    json.dumps(comps, separators=(",", ":"))])
        f.flush()
        print(f"  t_s={t_s:5d} workers={workers} execs={execs} pods={pods} "
              f"cap_max={cap_max}")

        # sleep in short slices so a stop signal is honoured promptly
        slept = 0.0
        while slept < args.interval and not _stop:
            time.sleep(min(0.5, args.interval - slept))
            slept += 0.5
    f.close()


def read_state(state_path):
    rows = []
    with open(state_path) as f:
        for r in csv.DictReader(f):
            comps = json.loads(r["components_json"]) if r.get("components_json") else {}
            rows.append({
                "t_s": _int(r["t_s"]),
                "workers": _int(r.get("workers_total")),
                "pods": _int(r.get("supervisor_pods")),
                "cap_max": _float(r.get("capacity_max")),
                "comps": comps,
            })
    rows.sort(key=lambda x: (x["t_s"] if x["t_s"] is not None else 0))
    return rows


def derive_rebalances(rows, run_id, condition, group):
    out = []
    for prev, cur in zip(rows, rows[1:]):
        t_s = cur["t_s"]
        # ARiSto: per-component executor changes
        for comp in sorted(set(prev["comps"]) | set(cur["comps"])):
            a, b = prev["comps"].get(comp), cur["comps"].get(comp)
            if a is None or b is None or a == b:
                continue
            out.append(_row(run_id, condition, group, t_s, "aristo",
                            comp, a, b, cur["cap_max"]))
        # ARiSto: worker count change
        if prev["workers"] is not None and cur["workers"] is not None \
                and prev["workers"] != cur["workers"]:
            out.append(_row(run_id, condition, group, t_s, "aristo",
                            "workers", prev["workers"], cur["workers"], cur["cap_max"]))
        # KEDA: supervisor pod change (trigger_value = weight_scale not polled -> blank)
        if prev["pods"] is not None and cur["pods"] is not None \
                and prev["pods"] != cur["pods"]:
            out.append(_row(run_id, condition, group, t_s, "keda",
                            "supervisor", prev["pods"], cur["pods"], None))
    return out


def _row(run_id, condition, group, t_s, layer, component, frm, to, trigger):
    return {
        "run_id": run_id, "condition": condition, "group": group, "t_s": t_s,
        "layer": layer,
        "action": "scale_out" if to > frm else "scale_in",
        "component": component, "from_count": frm, "to_count": to,
        "trigger_value": "" if trigger is None else round(trigger, 4),
    }


def finalize(args, state_path, reb_path):
    if not os.path.exists(state_path):
        print(f"No state file at {state_path}; nothing to finalize.", file=sys.stderr)
        return
    rows = read_state(state_path)
    reb = derive_rebalances(rows, args.run_id, args.condition, args.group)
    with open(reb_path, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=REB_HEADER)
        wr.writeheader()
        wr.writerows(reb)
    aristo = sum(1 for r in reb if r["layer"] == "aristo")
    keda = sum(1 for r in reb if r["layer"] == "keda")
    print(f"\nDerived {len(reb)} rebalance events "
          f"(aristo={aristo}, keda={keda}) from {len(rows)} state rows → {reb_path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--condition", required=True)
    ap.add_argument("--group", required=True)
    ap.add_argument("--t0", type=float, default=None,
                    help="load-start epoch (align with export_run --start). "
                         "Default: now (t_s starts at 0 when poller starts).")
    ap.add_argument("--storm-url", default="http://localhost:8081")
    ap.add_argument("--topology", default="iot-smarthome")
    ap.add_argument("--namespace", default="storm-cluster")
    ap.add_argument("--sts", default="supervisor", help="supervisor StatefulSet name")
    ap.add_argument("--interval", type=float, default=15.0)
    ap.add_argument("--duration", type=float, default=None,
                    help="auto-stop after N seconds (else run until signalled)")
    ap.add_argument("--out", default=".")
    ap.add_argument("--finalize-only", action="store_true",
                    help="skip polling; derive rebalance CSV from existing state CSV")
    args = ap.parse_args()
    if args.t0 is None:
        args.t0 = time.time()

    os.makedirs(args.out, exist_ok=True)
    state_path = os.path.join(args.out, f"state_{args.run_id}.csv")
    reb_path = os.path.join(args.out, f"rebalance_{args.run_id}.csv")

    if args.finalize_only:
        finalize(args, state_path, reb_path)
        return

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)
    run_poller(args, state_path)
    finalize(args, state_path, reb_path)


if __name__ == "__main__":
    main()
