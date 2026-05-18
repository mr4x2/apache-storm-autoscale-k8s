[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/mr4x2/apache-storm-autoscale-k8s)

# Dynamic Multi-Level Autoscale Apache Storm in Kubernetes

A research and engineering project that runs an IoT smart-home data processing pipeline on Apache Storm with **two-level automatic scaling**: executor/worker scaling inside Storm (Java) and pod scaling in Kubernetes (KEDA).

## What It Does

IoT sensor data is published over MQTT, consumed by a Storm topology that computes rolling averages, sums, and forecasts across 8 time windows (1, 5, 10, 15, 20, 30, 60, 120 minutes), and stored in MySQL. The system automatically scales Storm workers and Kubernetes pods in response to load.

```
MQTT Publisher → MQTT Broker → Storm Topology → MySQL
                                    ↕
                         Two Autoscaling Layers
```

## Documentation

| Doc | Description |
|---|---|
| [Architecture](docs/architecture.md) | System diagrams, component overview, port reference |
| [Storm Topology](docs/storm-topology.md) | DAG structure, throughput targets, data format |
| [Java Autoscaler](docs/autoscaler-java.md) | Rule-based executor scaling — algorithm, classes, build |
| [KEDA Autoscaler](docs/autoscaler-keda.md) | Pod scaling — composite metric formula, configuration |
| [Monitoring](docs/monitoring.md) | Prometheus metrics, Grafana dashboards, storm-exporter |
| [Docker Compose Guide](docs/deployment-docker.md) | Local development setup |
| [Kubernetes Guide](docs/deployment-k8s.md) | K8s deployment, KEDA setup, custom images |
| [Related Projects](docs/related-projects.md) | Core topology repo and Prometheus exporter repo details |

## Quick Start (Local with Docker Compose)

### 1. Build the autoscaler

```bash
cd storm-src
mvn package
cd ..
```

### 2. Start the cluster

```bash
docker compose up -d
```

This starts: Zookeeper, Nimbus (+ Storm UI), 2 Supervisors, MQTT Broker, MySQL, and storm-exporter.

- Storm UI: http://localhost:8081
- storm-exporter (Prometheus metrics): http://localhost:8082

### 3. Deploy the IoT topology

```bash
docker exec -it nimbus bash
cd /opt/storm/lib/
storm jar Storm-IOTdata-1.0.jar com.storm.iotdata.MainTopo
```

> The topology JAR (`Storm-IOTdata-1.0.jar`) is from a separate project and must be built independently.

### 4. Run the autoscaler

```bash
docker exec -it nimbus bash
cd /opt/storm/lib/
storm jar storm-autoscale-1.0.jar org.apache.storm.starter.rulebase.v1.TopologyParser input.txt target.txt
```

## How Autoscaling Works

### Level 1 — Executor Scaling (Java, inside Storm)

The autoscaler (`storm-src/`) runs as a JAR inside Nimbus. Every 30 seconds it:

1. Fetches metrics for all topology components via Storm's Thrift API
2. Compares each spout's throughput against the target (4000 msgs/sec)
3. If throughput is consistently below target (severity ≥ 2), finds the most-loaded bolt by capacity and adds 1 executor to it
4. Adds a Storm worker if thread density exceeds 2 threads per slot
5. Calls `nimbus.rebalance()` to apply changes immediately

See [Java Autoscaler docs](docs/autoscaler-java.md) for the full algorithm.

### Level 2 — Pod Scaling (KEDA, Kubernetes)

A Python FastAPI service (`k8s/keda/custom-metrics/`) queries Prometheus and computes a composite `weight_scale` metric:

```
weight = 0.6 × (workerUtilization / 0.70)
       + 0.2 × (boltCapacity / 0.50)
       + 0.2 × (spoutLatency / 100ms)
```

KEDA scales the `supervisor` StatefulSet between 1 and 7 pods when `weight > 0.75`. Each new pod adds 4 worker slots.

See [KEDA Autoscaler docs](docs/autoscaler-keda.md) for configuration details.

## Project Structure

```
storm-src/           Java autoscaler + build config (Maven)
  src/main/java/org/apache/storm/starter/
    metric/          Metric POJOs and updaters (BoltMetrics, SpoutMetrics, ...)
    rulebase/v1/     Autoscale logic (TopologyParser, FlowCheck, RebalanceMove)
  src/main/resources/
    input.txt        Topology DAG edge list
    target.txt       Per-spout throughput targets

k8s/                 Kubernetes manifests
  storm-k8s.yml      All workloads (supervisor is a StatefulSet)
  storm-svc.yml      All services
  keda/              KEDA autoscaler components
    autoscale-keda.yaml          ScaledObject
    custom-metrics/main.py       Python KEDA controller
  monitoring/        Prometheus + Grafana manifests
  mqtt/              MQTT broker and publisher

deploy/              Docker-based deployment configs
  monitoring/        Prometheus + Grafana (Docker Compose)
  nimbus/            Nimbus Dockerfile
  supervisor/        Supervisor Dockerfile

config/              Storm configuration files
  storm-nimbus.yaml  Full Storm config (all defaults + overrides)
  storm-supervisor.yaml
```

## Kubernetes Deployment

See the full [Kubernetes deployment guide](docs/deployment-k8s.md).

```bash
kind create cluster --config k8s/kind-k8s-cluster.yml
kubectl create -f k8s/storm-ns.yml
kubectl create -f k8s/storm-svc.yml
kubectl create -f k8s/storm-pv.yml
kubectl create -f k8s/storm-pvc.yml
kubectl create -f k8s/storm-k8s.yml
kubectl apply -f k8s/keda/custom-metrics/autoscale-controller-deployment.yml
kubectl apply -f k8s/keda/autoscale-keda.yaml
```

External access:
- Storm UI: `http://<node-ip>:30001`
- MQTT: `<node-ip>:30002`

## Related Projects

This repository is the autoscaling layer in a three-repo research system:

| Repository | Role |
|---|---|
| [fimocode/stormsmarthome](https://github.com/fimocode/stormsmarthome) | **Core topology** — the original IoT Storm pipeline (MQTT → Storm → MySQL) with no autoscaling. Source of the topology JAR deployed here. |
| [mr4x2/storm_exporter_prometheus](https://github.com/mr4x2/storm_exporter_prometheus) | **Prometheus exporter** — scrapes Storm UI REST API and publishes all metrics including `weight_scale`, the composite metric that drives KEDA pod scaling. |
| apache-storm-autoscale-k8s *(this repo)* | **Autoscaling layer** — adds Java rule-based executor scaling + KEDA pod scaling on top of the core topology. |

See [docs/related-projects.md](docs/related-projects.md) for full details on both external repos.

## Technology Stack

- **Apache Storm 2.6.2** — distributed stream processing
- **Zookeeper** — Storm cluster coordination
- **MQTT (Mosquitto)** — IoT data ingestion
- **MySQL 8.4** — time-series storage
- **Prometheus + Grafana** — observability
- **KEDA** — Kubernetes event-driven autoscaling
- **Java 11 + Maven** — autoscaler source
- **Python 3 + FastAPI** — KEDA controller service
- **Node.js** — MQTT data publisher
