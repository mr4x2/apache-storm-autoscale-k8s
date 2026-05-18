# System Architecture

## Overview

This project runs an Apache Storm topology that processes IoT smart-home sensor data, with two autoscaling mechanisms operating at different levels simultaneously.

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA PIPELINE                            │
│                                                                 │
│  MQTT Publisher ──► MQTT Broker ──► Storm Spout                 │
│  (Node.js/CSV)      (Mosquitto)     (spout-data-iot-data)       │
│                      port 1883        │                         │
│                                       ▼                         │
│                              split-{1,5,10,15,20,30,60,120}     │
│                                       │                         │
│                                       ▼                         │
│                              avg-{1,5,10,15,20,30,60,120}       │
│                                       │                         │
│                            ┌──────────┴──────────┐             │
│                            ▼                     ▼             │
│                     sum-{...}             forecast-{...}        │
│                            │                     │             │
│                            └──────────┬──────────┘             │
│                                       ▼                         │
│                                    MySQL                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   MONITORING PIPELINE                           │
│                                                                 │
│  Storm UI (nimbus:8081)                                         │
│       │                                                         │
│       ▼                                                         │
│  storm-exporter (port 8082)  ──scrape every 3-5s               │
│       │                                                         │
│       ▼                                                         │
│  Prometheus (port 9090)  ──scrape every 15s                     │
│       │                                                         │
│       ├──────────────────────────────────────────┐             │
│       ▼                                          ▼             │
│  Grafana (dashboards)              KEDA Controller (port 8001)  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  DUAL AUTOSCALING SYSTEM                        │
│                                                                 │
│  LEVEL 1 — Executor scaling (Java, inside Storm)               │
│  TopologyParser ──(30s poll)──► FlowCheck                       │
│       │                              │                          │
│       │  NimbusClient Thrift API     │ severity >= 2?           │
│       │◄─ metrics ──────────────────┤                          │
│       │                              ▼                          │
│       └──► RebalanceMove ──► nimbus.rebalance()                 │
│                        (adjust executor counts)                 │
│                                                                 │
│  LEVEL 2 — Pod scaling (KEDA, Kubernetes)                       │
│  KEDA Controller ──(poll Prometheus)──► weight_scale metric     │
│       │                                                         │
│       ▼                                                         │
│  KEDA ScaledObject ──► HPA ──► supervisor StatefulSet           │
│                        (scale pods 1 → 7)                       │
└─────────────────────────────────────────────────────────────────┘
```

## Components

| Component | Image | Role |
|---|---|---|
| Zookeeper | `zookeeper` / `mr4x2/zookeeper-k8s:v1.1` | Storm coordination |
| Nimbus | `storm` / `mr4x2/nimbus-k8s:v2.2` | Storm master + UI + autoscale JAR |
| Supervisor | `storm` / `mr4x2/supervisor-k8s:v2.1` | Storm workers (StatefulSet in K8s) |
| MQTT Broker | `mr4x2/mqtt-broker-iotdata:v1` | IoT data ingestion |
| MySQL | `mysql:8.4.2` | Processed data storage |
| storm-exporter | `mr4x2/stormexporter:v1.4.1` | Prometheus metrics bridge |
| KEDA Controller | `mr4x2/keda-controller:v1` | Custom KEDA external scaler |
| Prometheus | `prom/prometheus` | Metrics storage |
| Grafana | `grafana/grafana` | Dashboards |

## Ports

| Port | Service | Notes |
|---|---|---|
| 1883 | MQTT Broker | nodePort 30002 in K8s |
| 2181 | Zookeeper | ClusterIP only |
| 3306 | MySQL | ClusterIP only |
| 6627 | Nimbus Thrift RPC | Internal, used by Storm clients |
| 6700–6703 | Supervisor slots | One slot = one worker process |
| 8001 | KEDA Controller | Python FastAPI |
| 8081 | Storm UI | nodePort 30001 in K8s |
| 8082 | storm-exporter | Prometheus scrape target |
| 9090 | Prometheus | |
| 3000 | Grafana | |

## Namespace and Networking

- **Docker Compose:** All services share the `storm_network` bridge network, resolved by container name.
- **Kubernetes:** All resources in namespace `storm-cluster`. Supervisor is a `StatefulSet` with a headless service (`supervisor-dns`) to support stable DNS per pod.
