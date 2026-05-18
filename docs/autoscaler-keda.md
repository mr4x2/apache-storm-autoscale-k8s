# KEDA Pod Autoscaler

Located in `k8s/keda/`.

## Purpose

Scales the `supervisor` StatefulSet (number of pods) in Kubernetes based on a composite metric computed from Prometheus data. This is **pod-level scaling** — adding more supervisor nodes, each providing 4 more worker slots.

## Components

| File | Role |
|---|---|
| `custom-metrics/main.py` | Python FastAPI service — KEDA external scaler HTTP server |
| `custom-metrics/autoscale-controller-deployment.yml` | K8s Deployment + Service for the FastAPI app |
| `autoscale-keda.yaml` | KEDA `ScaledObject` — defines the scaling policy |
| `config-hpa.yml` | HPA generated/managed by KEDA |

## How It Works

KEDA's external HTTP scaler polls the KEDA controller's `/getMetrics` endpoint. When the returned metric value exceeds the threshold, KEDA updates the supervisor StatefulSet replica count.

```
Prometheus
    │
    │ query (every 30s, cached)
    ▼
KEDA Controller (FastAPI, port 8001)
    │
    │ /getMetrics → { custom_metric: weight_scale_value }
    ▼
KEDA ScaledObject
    │ threshold: 0.75
    ▼
HPA → supervisor StatefulSet (min 1, max 7 replicas)
```

## Composite Metric Formula

> **Important:** `weight_scale` is computed and published to Prometheus by [`storm_exporter_prometheus`](https://github.com/mr4x2/storm_exporter_prometheus), not by the KEDA controller FastAPI. The KEDA `ScaledObject` queries it directly from Prometheus. The `k8s/keda/custom-metrics/main.py` FastAPI is an alternative/experimental approach that re-derives the same value from Prometheus queries.

```python
weight_scale = (slotsUsed / slotsTotal) * 0.6/0.7
             + (avg_bolt_capacity / 0.5) * 0.2
             + (avg_spout_complete_latency / 100) * 0.2
```

| Signal | Source metric | Threshold | Weight |
|---|---|---|---|
| Worker slot utilization | `worker_cluster_used / worker_cluster_total` | 0.70 | 60% |
| Avg capacity of `split-*` bolts | `bolts_capacity{BoltId=~"^split-.*"}` (600s window) | 0.50 | 20% |
| Spout complete latency | `spouts_complete_latency{SpoutId="spout-data-iot-data"}` (600s window) | 100 ms | 20% |

A value of `1.0` means all signals are exactly at their thresholds. KEDA triggers scaling at `> 0.75`.

## ScaledObject Configuration

```yaml
# k8s/keda/autoscale-keda.yaml
scaleTargetRef:
  name: supervisor
  kind: StatefulSet
minReplicaCount: 1
maxReplicaCount: 7
initialCooldownPeriod: 300   # 5 min before first scale
triggers:
  - type: prometheus
    threshold: "0.75"
    query: weight_scale{ClusterHost="nimbus-ui:8081"}
```

> Note: The ScaledObject uses a `prometheus` trigger type pointing at Prometheus directly (not the external HTTP scaler). The `weight_scale` metric must be pushed/exported to Prometheus by the KEDA controller or storm-exporter.

## HPA Behavior

```yaml
scaleUp:
  stabilizationWindowSeconds: 300   # wait 5 min before scaling up
  policies: [{ type: Pods, value: 1, periodSeconds: 300 }]  # +1 pod at a time
scaleDown:
  stabilizationWindowSeconds: 300
  policies: [{ type: Pods, value: 1, periodSeconds: 300 }]  # -1 pod at a time
```

## Configuration

Environment variables for the KEDA controller pod:

```
NIMBUS_HOST=nimbus-ui:8081
PROMETHEUS_HOST=http://prometheus:9090
```

For local testing, copy `k8s/keda/custom-metrics/sample.env` to `.env` and adjust `PROMETHEUS_HOST`.

## Running Locally (for testing the FastAPI service)

```bash
cd k8s/keda/custom-metrics
cp sample.env .env
# edit .env with correct PROMETHEUS_HOST

pip install -r requirements.txt
uvicorn main:app --port 8001
```

```bash
# Build and push image
docker build -t mr4x2/keda-controller:v1 .
docker push mr4x2/keda-controller:v1
```

## API Endpoints

| Endpoint | Response |
|---|---|
| `GET /isActive` | `{"isActive": true/false}` |
| `GET /getMetricSpec` | `[{"metricName": "custom_metric", "targetValue": 0.7}]` |
| `GET /getMetrics` | `{"metricValues": [{"metricName": "custom_metric", "metricValue": <float>}, ...]}` |
