```bash

  Install Java 11 + Maven (on Ubuntu/Debian — nimbus pod or a VM):
  apt-get update && apt-get install -y maven openjdk-11-jdk
  java -version   # should show 11
  mvn -version    # should show 3.x

  On macOS (your local machine, if building locally):
  brew install maven
  mvn -version 
  
  ---
  Build both JARs:
  cd storm-src
  mvn package -DskipTests
  
  Output in storm-src/target/:
  - storm-autoscale-v1-1.0.jar — custom aristo (modified windowed formula)
  - storm-autoscale-aristo-1.0.jar — original aristo (cumulative formula)
storm jar Storm-IOTdata-1.0-SNAPSHOT-jar-with-dependencies.jar com.storm.iotdata.MainTopo
  ---
  Copy both JARs into nimbus pod (run from your local machine after build):
  # Get nimbus pod name
  NIMBUS=$(kubectl get pod -n storm-cluster -l app=nimbus -o jsonpath='{.items[0].metadata.name}')
  
  # Copy both JARs
  kubectl cp target/storm-autoscale-v1-1.0.jar \
    storm-cluster/$NIMBUS:/app/
    
  kubectl cp target/storm-autoscale-aristo-1.0.jar \
    storm-cluster/$NIMBUS:/app/
    
  # Verify
  kubectl exec -n storm-cluster $NIMBUS -- ls /opt/storm/lib/ | grep storm-autoscale
  
  Build takes ~2-3 min on first run (downloads dependencies), ~30s on subsequent runs.
```


```bash
python3 export_run.py \
    --run-id G1-autoscale-r1 \
    --condition non-static \
    --group G1 \
    --replicate 1 \
    --start 1784051797 \
    --end   1784053601 \
    --prom  http://localhost:9090 \
    --out   docs/experiment-results/G1/autoscale-aristo/
```

```bash
NIMBUS_POD=$(kubectl get pod -n storm-cluster -l app=nimbus -o jsonpath='{.items[0].metadata.name}')

kubectl cp target/storm-autoscale-v1-1.0.jar storm-cluster/${NIMBUS_POD}:/app/storm-autoscale-v1-1.0.jar

kubectl cp target/storm-autoscale-aristo-1.0.jar storm-cluster/${NIMBUS_POD}:/app/storm-autoscale-aristo-1.0.jar

kubectl exec -n storm-cluster $NIMBUS -- bash -c \
    "nohup storm jar /app/storm-autoscale-v1-1.0.jar \
     org.apache.storm.starter.rulebase.v1.TopologyParser \
     input.txt target.txt > /autoscale-aristo-1.0.log 2>&1 &"
```

```bash
# On GCE VM — record start time
start_epoch=$(date +%s)
echo "START: $start_epoch"
  
# Step 1: 1000 msg/s (1 publisher × 1000)
sed -i 's/SPEED=.*/SPEED=1000/' mqtt.env
docker compose --env-file mqtt.env up building_1 -d
echo "Load step 1 started (1000 msg/s) — wait 10 min"
sleep 600

# Step 2: 4000 msg/s (4 publishers × 1000)
docker compose --env-file mqtt.env up building_2 building_3 building_4 -d
echo "Load step 2 started (4000 msg/s) — wait 10 min"
sleep 600

# Step 3: 8000 msg/s (8 publishers × 1000)
docker compose --env-file mqtt.env up building_5 building_6 building_7 building_8 -d
echo "Load step 3 started (8000 msg/s) — wait 10 min"
sleep 600

# Record end time
end_epoch=$(date +%s)
echo "END: $end_epoch"
  
# Stop publishers
docker compose --env-file mqtt.env down
```


```bash
Step 1 — Reset cluster (every run)

  NIMBUS_POD=$(kubectl get pod -n storm-cluster -l app=nimbus -o jsonpath='{.items[0].metadata.name}')

  # Kill autoscaler if running
  kubectl exec -n storm-cluster $NIMBUS_POD -- pkill -f TopologyParser || true

  # Remove KEDA ScaledObject (for non-KEDA conditions)
  kubectl delete -f k8s/keda/autoscale-keda.yaml --ignore-not-found

  # Reset supervisor to 1 replica
  kubectl scale statefulset supervisor -n storm-cluster --replicas=1

  # Kill topology and redeploy
  kubectl exec -n storm-cluster $NIMBUS_POD -- storm kill iot-smarthome -w 30
  sleep 60
  kubectl exec -n storm-cluster $NIMBUS_POD -- \
    storm jar /app/Storm-IOTdata-1.0.jar com.storm.iotdata.MainTopo
storm jar Storm-IOTdata-1.0-SNAPSHOT-jar-with-dependencies.jar com.storm.iotdata.MainTopo

  # Stop publisher
  ssh <GCE-VM> "cd ~/mqtt && docker compose --env-file mqtt.env down"

  # Wait for topology to be ACTIVE
  sleep 30
  
  Step 2 — Set condition switches

  ┌─────────────┬──────────────────────┬────────────────────┐
  │  Condition  │        ARiSto        │        KEDA        │
  ├─────────────┼──────────────────────┼────────────────────┤
  │ static      │ nothing              │ nothing            │
  ├─────────────┼──────────────────────┼────────────────────┤
  │ aristo_only │ start autoscaler JAR │ nothing            │
  ├─────────────┼──────────────────────┼────────────────────┤
  │ keda_only   │ nothing              │ apply ScaledObject │
  ├─────────────┼──────────────────────┼────────────────────┤
  │ dynamix     │ start autoscaler JAR │ apply ScaledObject │
  └─────────────┴──────────────────────┴────────────────────┘
  
  For aristo_only / dynamix — start autoscaler in background:
  kubectl exec -n storm-cluster $NIMBUS_POD -- bash -c \
    "nohup storm jar /storm-autoscale-v1-1.0.jar \
     org.apache.storm.starter.rulebase.v1.TopologyParser \
     input.txt target.txt > /autoscaler-v1.log 2>&1 &"

  For keda_only / dynamix — apply ScaledObject:
  kubectl apply -f k8s/keda/autoscale-keda.yaml

  Step 3 — Record start and run load ramp

  # On GCE VM — record start time
  start_epoch=$(date +%s)
  echo "START: $start_epoch"

  # Step 1: 1000 msg/s (1 publisher × 1000)
  sed -i 's/SPEED=.*/SPEED=1000/' ~/mqtt/mqtt.env
  docker compose --env-file ~/mqtt/mqtt.env up building_1 -d
  echo "Load step 1 started (1000 msg/s) — wait 10 min"
  sleep 600

  # Step 2: 4000 msg/s (4 publishers × 1000)
  docker compose --env-file ~/mqtt/mqtt.env up building_2 building_3 building_4 -d
  echo "Load step 2 started (4000 msg/s) — wait 10 min"
  sleep 600

  # Step 3: 8000 msg/s (8 publishers × 1000)
  docker compose --env-file ~/mqtt/mqtt.env up building_5 building_6 building_7 building_8 -d
  echo "Load step 3 started (8000 msg/s) — wait 10 min"
  sleep 600

  # Record end time
  end_epoch=$(date +%s)
  echo "END: $end_epoch"
  
  # Stop publishers
  docker compose --env-file ~/mqtt/mqtt.env down

  Step 4 — Export data (run from GCE VM after each run)

  # Example for G1-static-r1 — substitute run_id/condition/replicate each time
  python3 export_run.py \
    --run-id G1-static-r1 \
    --condition static \
    --group G1 \
    --replicate 1 \
    --start $start_epoch \
    --end   $end_epoch \
    --prom  http://34.126.115.181:30003 \
    --out   docs/experiment-results/G1/static/

  Then manually append the printed metadata row to docs/experiment-results/run_metadata.csv.

  Also copy the rebalance log for aristo conditions:
  kubectl cp storm-cluster/$NIMBUS_POD:/iot-smarthome_aristo_rb.txt \
    docs/experiment-results/G1/aristo_only/rebalance_G1-aristo_only-r1_raw.txt
```