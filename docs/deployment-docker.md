# Local Development with Docker Compose

## Prerequisites

- Docker + Docker Compose
- Maven (for building `storm-src`)

## Quick Start

```bash
# 1. Build the autoscaler JAR first
cd storm-src && mvn package && cd ..

# 2. Start the full stack
docker compose up -d

# 3. Verify all containers are up
docker compose ps
```

Services started:
- `zookeeper` — coordination
- `nimbus` — Storm master + UI at http://localhost:8081
- `supervisor`, `supervisor2` — two worker nodes
- `mqtt-broker` — MQTT at localhost:1883
- `mysql` — database at localhost:3306
- `storm-exporter` — Prometheus metrics at http://localhost:8082

## Deploy the Topology

The topology JAR (`Storm-IOTdata-1.0.jar`) is a **separate project** that must be built separately and placed at `storm-src/target/Storm-IOTdata-1.0-SNAPSHOT-jar-with-dependencies.jar`.

```bash
docker exec -it nimbus bash
cd /opt/storm/lib/
storm jar Storm-IOTdata-1.0.jar com.storm.iotdata.MainTopo
```

Verify the topology is running at http://localhost:8081 (Storm UI).

## Run the Java Autoscaler

```bash
docker exec -it nimbus bash
cd /opt/storm/lib/
storm jar storm-autoscale-1.0.jar org.apache.storm.starter.rulebase.v1.TopologyParser input.txt target.txt
```

The autoscaler connects to Nimbus via Thrift (port 6627) and polls every 30 seconds. Output is printed to stdout.

## Start the MQTT Publisher

```bash
cd k8s/mqtt/publisher

# Publish from CSV at default speed
node index.js -f /path/to/house-1.csv

# Options:
#   -f <file>     CSV data file path
#   -s <speed>    msgs/sec (0 = unlimited)
#   -b <url>      MQTT broker URL (default: mqtt-broker)
#   -t <topic>    MQTT topic (default: iot-data)
#   -h <hwm>      high-water mark for readline (default: 200)
#   -q <0|1|2>    QoS level
```

The publisher resumes from where it left off (saves offset to `.publish.stat`).

## MySQL Credentials

| Parameter | Value |
|---|---|
| Host | `localhost:3306` |
| Database | `iotdata` |
| User | `user1` |
| Password | `Uet123` |
| Root password | `Uet123` |

## Monitoring (Optional)

A separate monitoring stack is available in `deploy/monitoring/`:

```bash
cd deploy/monitoring
docker compose up -d
```

This starts Prometheus + Grafana with Storm dashboard pre-configured. Grafana is available at http://localhost:3000.

## Volume

MySQL data is persisted in a named Docker volume `mysql_data`. To reset: `docker compose down -v`.

## Updating the Autoscaler JAR

After changing Java code:

```bash
cd storm-src && mvn package && cd ..
docker compose restart nimbus
```

The JAR is mounted into the container at startup, so a restart picks up the new file.
