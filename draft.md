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
    --run-id G1-aristo_only-r1 \
    --condition aristo_only \
    --group G1 \
    --replicate 1 \
    --start 1784739962 \
    --end   1784741763 \
    --prom  http://localhost:9090 \
    --out   docs/experiment-results/G1/aristo_only/
```

```bash
--group G1 --condition static   --replicate 1 --run-id G1-static-r1      --start <s> --end <e> --out docs/experiment-results/G1/static/
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
  
# Step 1: 100 msg/s (1 publisher × 100)
sed -i 's/SPEED=.*/SPEED=100/' mqtt.env
docker compose --env-file mqtt.env up building_1 -d
echo "Load step 1 started (100 msg/s) — wait 10 min"
sleep 600

# Step 2: 400 msg/s (4 publishers × 100)
docker compose --env-file mqtt.env up building_2 building_3 building_4 -d
echo "Load step 2 started (4000 msg/s) — wait 10 min"
sleep 600

# Step 3: 8000 msg/s (8 publishers × 100)
docker compose --env-file mqtt.env up building_5 building_6 building_7 building_8 -d
echo "Load step 3 started (8000 msg/s) — wait 10 min"
sleep 600

# Record end time
end_epoch=$(date +%s)
echo "END: $end_epoch"
  
# Stop publishers
docker compose --env-file mqtt.env down
```




```cmd
kubectl config unset clusters.kind-storm.certificate-authority-data
kubectl config set-cluster kind-storm \
  --server=https://35.185.183.166:6443 \
  --insecure-skip-tls-verify=true
kubectl get nodes
```

Sửa lại env, tăng cường độ ở part2 và part 3 thử xem



sed -i 's/SPEED=.*/SPEED=100/' mqtt.env
docker compose --env-file mqtt.env up building_1 -d;                                    sleep 600
docker compose --env-file mqtt.env up building_3 building_4 building_2 -d;              sleep 600
docker compose --env-file mqtt.env up building_5 building_6 building_7 building_8 -d;   sleep 600
docker compose --env-file mqtt.env down          # stop publishers

CSV_FILE_0=house-0.csv
CSV_FILE_1=house-1.csv
CSV_FILE_2=house-2.csv
CSV_FILE_3=house-3.csv
CSV_FILE_4=house-4.csv
CSV_FILE_5=house-5.csv
CSV_FILE_6=house-6.csv
CSV_FILE_7=house-7.csv
CSV_FILE_8=house-8.csv
CSV_FILE_9=house-9.csv
CSV_FILE_10=house-10.csv

```bash
sed -i 's/SPEED=.*/SPEED=100/' mqtt.env
docker compose --env-file mqtt.env up building_1 building_2 building_3 building_4 building_5 -d;  sleep 1800
docker compose --env-file mqtt.env down;
sudo shutdown -h now
```

  cd /Users/mr8/project/storm_exporter_prometheus
  # build a new tag
  docker build -t mr4x2/stormexporter:v1.2.6 .

  # get it to the cluster — pick one:
  #   (kind on the VM)  kind load docker-image mr4x2/stormexporter:v1.2.6 --name storm
  #   (registry)        docker push mr4x2/stormexporter:v1.2.6

  # point the deployment at the new tag + restart
  kubectl set image deployment/storm-exporter storm-exporter=mr4x2/stormexporter:v1.2.6 -n storm-cluster
  kubectl rollout status deployment/storm-exporter -n storm-cluster


docs/g1-known-issues.md