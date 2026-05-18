# Deploy

This directory contains Dockerfiles for custom Storm images and a standalone monitoring stack.

For the full local dev setup using Docker Compose, see [`docs/deployment-docker.md`](../docs/deployment-docker.md).

---

## Custom Images

Each subdirectory has a Dockerfile that builds a pre-configured image for deployment outside of Docker Compose (e.g. running containers individually on separate machines).

### Build and run

**Zookeeper**
```bash
cd zookeeper/
docker build -t mr4x2/zookeeper:v1 .
docker run -d -p 2181:2181 --name zookeeper mr4x2/zookeeper:v1
```

**Nimbus**
```bash
cd nimbus/
docker build -t mr4x2/nimbus:v2 .
docker run -d -p 6627:6627 -p 8081:8081 --name nimbus mr4x2/nimbus:v2
```

**Supervisor**
```bash
cd supervisor/
docker build -t mr4x2/supervisor:v1 .
docker run -d -p 6700-6703:6700-6703 --name supervisor mr4x2/supervisor:v1
```

**storm-exporter**
```bash
# Edit storm_exporter.env to set STORM_UI_HOST
docker run -d -p 8082:8082 --env-file storm_exporter.env --name storm-exporter mr4x2/stormexporter:v1.4.1
```

`storm_exporter.env` variables:

| Variable | Description |
|---|---|
| `STORM_UI_HOST` | Storm UI address (e.g. `nimbus:8081`) |
| `PORT_EXPOSE` | Port to expose Prometheus metrics (default `8082`) |
| `REFRESH_RATE` | Seconds between Storm UI polls (default `5`) |

---

## Monitoring Stack

`monitoring/` runs Prometheus, Grafana, node_exporter, and cAdvisor as a standalone Docker Compose stack.

> Requires an external Docker network named `monitoring` to be created first.

```bash
docker network create monitoring

cd monitoring/
docker compose up -d
```

| Service | Port | Description |
|---|---|---|
| Prometheus | `9090` | Metrics storage |
| Grafana | `3000` | Dashboards (import `config/Apache-storm-grafana.json`) |
| node_exporter | — | Host-level metrics |
| cAdvisor | — | Container metrics |

The Grafana Storm dashboard JSON is at `monitoring/config/Apache-storm-grafana.json`.
