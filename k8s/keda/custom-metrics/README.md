# KEDA Controller

A FastAPI service that acts as a custom metrics source for KEDA, computing a composite `weight_scale` value from Prometheus to drive supervisor pod scaling.

Full details: [`docs/autoscaler-keda.md`](../../../../docs/autoscaler-keda.md)

## Setup

```bash
cp sample.env .env
# Edit .env with your PROMETHEUS_HOST
```

| Variable | Description |
|---|---|
| `NIMBUS_HOST` | Storm UI address (e.g. `nimbus-ui:8081`) |
| `PROMETHEUS_HOST` | Prometheus URL (e.g. `http://prometheus:9090`) |

## Run Locally

```bash
pip install -r requirements.txt
uvicorn main:app --port 8001
```

## Docker

```bash
# Build and push
docker build -t mr4x2/keda-controller:v1 .
docker push mr4x2/keda-controller:v1

# Run
docker run -d -p 8001:8001 --env-file .env --name keda-controller mr4x2/keda-controller:v1
```

## Deploy to Kubernetes

```bash
kubectl apply -f autoscale-controller-deployment.yml
kubectl apply -f ../autoscale-keda.yaml
```

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /isActive` | Returns `{"isActive": true}` if `weight_scale > 0.7` |
| `GET /getMetricSpec` | Returns metric name and target value |
| `GET /getMetrics` | Returns current `weight_scale` value |

## Composite Metric

```
weight_scale = 0.6 × (workerUsed / 0.7)
             + 0.2 × (boltCapacity / 0.5)
             + 0.2 × (spoutLatency / 100ms)
```

KEDA scales the `supervisor` StatefulSet (min 1, max 7 pods) when `weight_scale > 0.75`.

> Note: `weight_scale` is also computed and published directly to Prometheus by [`storm_exporter_prometheus`](https://github.com/mr4x2/storm_exporter_prometheus). The KEDA `ScaledObject` queries it from there. This service is an alternative HTTP-based path.
