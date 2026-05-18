# Monitoring

## Stack

- **storm-exporter** (`mr4x2/stormexporter`, source: [storm_exporter_prometheus](https://github.com/mr4x2/storm_exporter_prometheus)) — scrapes Storm's UI REST API and exposes metrics in Prometheus format. Also computes and publishes the `weight_scale` metric used by KEDA.
- **Prometheus** — stores time-series metrics
- **Grafana** — dashboards (includes a pre-built Apache Storm dashboard)

## storm-exporter Metrics

> Source code: [mr4x2/storm_exporter_prometheus](https://github.com/mr4x2/storm_exporter_prometheus). Full metric reference is in [`docs/related-projects.md`](related-projects.md).

The exporter polls `http://<STORM_UI_HOST>/api/v1/topology/summary` and component endpoints.

Key metrics exposed:

| Metric | Labels | Description |
|---|---|---|
| `bolts_capacity` | `BoltId`, `TopologyId` | Executor capacity (0.0–1.0+) |
| `spouts_complete_latency` | `SpoutId`, `TopologyId` | End-to-end tuple latency (ms) |
| `worker_cluster_used` | `ClusterHost` | Workers currently in use |
| `worker_cluster_total` | `ClusterHost` | Total available workers |
| `bolts_execute_latency` | `BoltId` | Bolt execute latency (ms) |
| `bolts_acked` | `BoltId` | Total acked tuples |
| `spouts_acked` | `SpoutId` | Total acked tuples |

## Configuration

### Docker Compose
```yaml
storm-exporter:
  image: mr4x2/stormexporter:v1.4.1
  environment:
    STORM_UI_HOST: nimbus:8081
    PORT_EXPOSE: 8082
    REFRESH_RATE: 3        # seconds between scrapes of Storm UI
```

### Kubernetes
```yaml
# k8s/monitoring/storm-exporter/storm-exporter-deployment.yml
env:
  - name: STORM_UI_HOST
    value: "nimbus-ui:8081"
  - name: REFRESH_RATE
    value: "5"
```

## Prometheus Scrape Config

```yaml
# k8s/monitoring/prom-grafana/configMap/prom-cm.yml
scrape_configs:
  - job_name: 'storm-metric'
    static_configs:
      - targets: ['storm-exporter:8082']
  - job_name: 'node_exporter'
    static_configs:
      - targets: ['node-exporter:9100']
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
```

## Grafana Dashboards

The Grafana dashboard JSON is at `deploy/monitoring/config/Apache-storm-grafana.json`. It can be imported via Grafana's dashboard import UI.

A second dashboard for K8s pod metrics is at `k8s/monitoring/prom-grafana/kubelet-metrics/k8s-pod-metrics-grafana.json`.

## Key Prometheus Queries (used by KEDA Controller)

```promql
# Worker utilization ratio
worker_cluster_used{ClusterHost="nimbus-ui:8081"}
worker_cluster_total{ClusterHost="nimbus-ui:8081"}

# Average bolt capacity (split bolts, 10-min window)
avg(avg_over_time(bolts_capacity{BoltId=~"^split-.*"}[10m]))

# Spout end-to-end latency (10-min window)
avg_over_time(spouts_complete_latency{SpoutId="spout-data-iot-data"}[10m])
```

## Running the Monitoring Stack (Docker Compose)

```bash
cd deploy/monitoring
docker compose up -d
# Grafana: http://localhost:3000 (admin/admin default)
# Prometheus: http://localhost:9090
```

## Autoscaling Thresholds

The KEDA controller treats these as scale-trigger thresholds:

| Signal | Scale threshold |
|---|---|
| Worker utilization | 70% |
| Bolt capacity (split-*) | 0.50 |
| Spout complete latency | 100 ms |

The composite weight (see [autoscaler-keda.md](autoscaler-keda.md)) exceeds 0.75 when any combination of signals approaches their thresholds.
