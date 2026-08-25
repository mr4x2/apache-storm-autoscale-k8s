# Runbook — Group 1 (P0 baseline)

G1 = 4 conditions × 3 replicates = 12 runs. Same load ramp every run; only the
**toggles** differ.

| Condition | ARiSto autoscaler | KEDA | Supervisor |
|---|---|---|---|
| `static` | off | off | fixed = 3 |
| `keda_only` | off | on | KEDA-managed |
| `aristo_only` | modified v1 on | off | fixed = 3 |
| `dynamix` | modified v1 on | on | KEDA-managed |

**Two machines:**
- **[VM]** GCP instance — runs only the docker-compose **load ramp** (`mqtt.env` + `building_*`).
- **[Mac]** your laptop (Freelens) — runs everything else over kubectl + port-forwards: toggles, autoscaler, **poller / export_run / merge**, topology reset.

Epoch coordination: `start_epoch` is recorded on the **[Mac]** and reused for both
`--t0` (poller) and `--start` (export). Clocks are NTP-synced, so the VM load just
needs to start at ~the same moment (within a 15 s poll — no exact handshake needed).

---

## Once per session — [Mac]

```bash
cd ~/project/apache-storm-autoscale-k8s      # repo on the Mac
export NS=storm-cluster
export NIMBUS=$(kubectl get pod -n $NS -l app=nimbus -o jsonpath='{.items[0].metadata.name}')
export VENV=$PWD/venv/bin/python3
# port-forwards via Freelens (or CLI), leave running:
#   kubectl port-forward -n storm-cluster svc/nimbus-ui  8081:8081
#   kubectl port-forward -n storm-cluster svc/prometheus 9090:9090
```

## Once per session — [VM]

```bash
cd ~/project/apache-storm-autoscale-k8s      # repo on the VM (has mqtt.env + docker compose)
```

---

## Per run — the 4 conditions — [Mac]

For each: set `RUN_ID`/`REP`/`OUT`, apply the toggles, then run the **capture block** below.

### A. `static`
```bash
export RUN_ID=G1-static-r1 REP=1 COND=static OUT=docs/experiment-results/G1/static; mkdir -p $OUT
kubectl delete -f k8s/keda/autoscale-keda.yaml -n $NS --ignore-not-found   # KEDA off
kubectl scale statefulset supervisor -n $NS --replicas=3                    # fixed infra
# no autoscaler
```

### B. `keda_only`
```bash
export RUN_ID=G1-keda_only-r1 REP=1 COND=keda_only OUT=docs/experiment-results/G1/keda_only; mkdir -p $OUT
kubectl apply -f k8s/keda/autoscale-keda.yaml -n $NS                        # KEDA on
# no autoscaler
```

### C. `aristo_only`
```bash
export RUN_ID=G1-aristo_only-r1 REP=1 COND=aristo_only OUT=docs/experiment-results/G1/aristo_only; mkdir -p $OUT
kubectl delete -f k8s/keda/autoscale-keda.yaml -n $NS --ignore-not-found   # KEDA off
kubectl scale statefulset supervisor -n $NS --replicas=3                    # fixed infra
kubectl exec -n $NS $NIMBUS -- bash -c \
  "nohup storm jar /app/storm-autoscale-v1-1.0.jar org.apache.storm.starter.rulebase.v1.TopologyParser input.txt target.txt > /app/autoscale.log 2>&1 &"
```

### D. `dynamix`
```bash
export RUN_ID=G1-dynamix-r2 REP=2 COND=dynamix OUT=docs/experiment-results/G1/dynamix; mkdir -p $OUT
kubectl apply -f k8s/keda/autoscale-keda.yaml -n $NS                        # KEDA on
kubectl exec -n $NS $NIMBUS -- bash -c \
  "nohup storm jar /app/storm-autoscale-v1-1.0.jar org.apache.storm.starter.rulebase.v1.TopologyParser input.txt target.txt > /app/autoscale.log 2>&1 &"
```

---

## Capture block — 3 steps across both machines

**Step 1 — [Mac] start the poller** (records `start_epoch`, used for both `--t0` and export `--start`):
```bash
start_epoch=$(date +%s); echo "START: $start_epoch"
$VENV storm_snapshot.py --run-id $RUN_ID --condition $COND --group G1 \
  --t0 $start_epoch --out $OUT > $OUT/poller_$RUN_ID.log 2>&1 &
SNAP=$!
```

**Step 2 — [VM] run the load ramp** (start it right after Step 1; ~30 min):
```bash
sed -i 's/SPEED=.*/SPEED=100/' mqtt.env
docker compose --env-file mqtt.env up building_1 building_2 -d;                                    sleep 600
docker compose --env-file mqtt.env up building_3 building_4 building_5 -d;              sleep 600
docker compose --env-file mqtt.env up building_5 building_6 building_7 building_8 -d;   sleep 600
docker compose --env-file mqtt.env down          # stop publishers
```

**Step 3 — [Mac] stop poller, export, merge, reset** (once the VM ramp finished):
```bash
end_epoch=$(date +%s); echo "END: $end_epoch"
kill $SNAP                                        # poller writes rebalance_$RUN_ID.csv

$VENV export_run.py --run-id $RUN_ID --condition $COND --group G1 \
  --replicate $REP --start $start_epoch --end $end_epoch --prom http://localhost:9090 --out $OUT
$VENV merge_run.py --timeseries $OUT/timeseries_$RUN_ID.csv --state $OUT/state_$RUN_ID.csv

# cleanup for next run:
kubectl exec -n $NS $NIMBUS -- pkill -f rulebase.v1.TopologyParser || true   # aristo_only/dynamix only
kubectl exec -n $NS $NIMBUS -- storm kill iot-smarthome -w 30 || true; sleep 40
kubectl exec -n $NS $NIMBUS -- bash -c \
  "cd /app && storm jar Storm-IOTdata-1.0-SNAPSHOT-jar-with-dependencies.jar com.storm.iotdata.MainTopo"
sleep 90
```

Then append the metadata line `export_run` printed to
`docs/experiment-results/run_metadata.csv` (edit `keda_enabled`/`aristo_jar` per
condition: keda→true for keda_only/dynamix; aristo_jar→`storm-autoscale-v1-1.0.jar`
for aristo_only/dynamix).

---

## Replicates & order

Repeat all 4 conditions for `r1`, `r2`, `r3` — change only `RUN_ID` (`…-r2`/`-r3`)
and `REP` (`2`/`3`). 12 runs total.

## After all 12 — tables + figures
```bash
cd analysis
$VENV dynamix_analysis.py ../docs/experiment-results ../docs/metrics-schema.json
$VENV dynamix_plots.py    ../docs/experiment-results ../docs/metrics-schema.json
```

## Notes
- Output must stay in `docs/experiment-results/G1/<condition>/` subdirs (the loader double-counts files at the data root).
- `--t0` (poller) = `--start` (export) = `start_epoch`, so `t_s` aligns for the merge.
- Confirm load actually ramped (avoid the idle 30 msg/s case):
  `curl -s 'http://localhost:9090/api/v1/query?query=sum(rate(spouts_acked%7BSpoutId%3D%22spout-data-iot-data%22%7D%5B1m%5D))'`
- If a run dies mid-way, rebuild its rebalance file from the state CSV:
  `$VENV storm_snapshot.py --run-id $RUN_ID --condition $COND --group G1 --out $OUT --finalize-only`


There is a problem I need you to clarify for me.

in G1 other test I run in 30 mins but for dynamix, cause scaling in pod I must run in 1600+600+600 mins(you can check runhook-G1). Therefore it maybe not sync in time range for running experiments. anyway to solve this problem?