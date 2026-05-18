# Kubernetes Deployment

## Prerequisites

- `kubectl`
- `kind` (for local cluster)
- KEDA installed in the cluster (`kubectl apply -f https://github.com/kedacore/keda/releases/download/v2.x.x/keda-2.x.x.yaml`)

## 1. Create Local Cluster

```bash
cd k8s/
kind create cluster --config kind-k8s-cluster.yml
```

## 2. Deploy Storm Cluster

```bash
kubectl create -f k8s/storm-ns.yml       # namespace: storm-cluster
kubectl create -f k8s/storm-svc.yml      # all services
kubectl create -f k8s/storm-pv.yml       # PersistentVolume (MySQL)
kubectl create -f k8s/storm-pvc.yml      # PersistentVolumeClaim
kubectl create -f k8s/storm-k8s.yml      # zookeeper, nimbus, supervisor StatefulSet, mysql, mqtt-broker
```

After deployment:
- Storm UI: `http://<node-ip>:30001`
- MQTT Broker: `<node-ip>:30002`

## 3. Deploy Monitoring Stack

```bash
# Prometheus ConfigMap
kubectl apply -f k8s/monitoring/prom-grafana/configMap/prom-cm.yml
kubectl apply -f k8s/monitoring/prom-grafana/configMap/datasource-cm.yml

# RBAC for Prometheus to scrape kubelet metrics
kubectl apply -f k8s/monitoring/prom-grafana/kubelet-metrics/

# Persistent volumes
kubectl apply -f k8s/monitoring/prom-grafana/monitoring-pv.yml
kubectl apply -f k8s/monitoring/prom-grafana/monitoring-pvc.yml

# Deployments and services
kubectl apply -f k8s/monitoring/prom-grafana/prometheus-deployment.yml
kubectl apply -f k8s/monitoring/prom-grafana/monitoring-svc.yml
kubectl apply -f k8s/monitoring/prom-grafana/svc/

# Storm exporter
kubectl apply -f k8s/monitoring/storm-exporter/storm-exporter-deployment.yml
kubectl apply -f k8s/monitoring/storm-exporter/storm-exporter-svc.yml
```

## 4. Deploy KEDA Autoscaler

```bash
# KEDA controller (custom metrics FastAPI service)
kubectl apply -f k8s/keda/custom-metrics/autoscale-controller-deployment.yml

# KEDA ScaledObject (scales supervisor StatefulSet)
kubectl apply -f k8s/keda/autoscale-keda.yaml
```

## 5. Deploy MQTT Publisher

```bash
kubectl apply -f k8s/mqtt/broker/mqtt-broker-pod.yaml
kubectl apply -f k8s/mqtt/broker/mqtt-broker-svc.yaml
kubectl apply -f k8s/mqtt/mqtt-deployment.yaml
kubectl apply -f k8s/mqtt/mqtt-svc.yaml
```

## 6. Deploy Topology

```bash
kubectl exec -it <nimbus-pod> -n storm-cluster -- bash
cd /opt/storm/lib/
storm jar Storm-IOTdata-1.0.jar com.storm.iotdata.MainTopo
```

## Key Resources

| Resource | Kind | Notes |
|---|---|---|
| `supervisor` | StatefulSet | Scaled by KEDA; headless service `supervisor-dns` |
| `nimbus` | Deployment | 1 replica; includes autoscale JAR in v2.2 image |
| `zookeeper` | Deployment | 1 replica |
| `mysql` | Deployment | Uses PVC `mysql-pvc` |
| `mqtt-broker` | Deployment | NodePort 30002 |
| `storm-exporter` | Deployment | Prometheus scrape target |
| `keda-controller` | Deployment | Python FastAPI, ClusterIP port 8001 |

## Scaling the Supervisor Manually

```bash
kubectl scale statefulset supervisor -n storm-cluster --replicas=3
```

## Checking KEDA Status

```bash
kubectl get scaledobject -n storm-cluster
kubectl describe scaledobject storm-supervisor-scaledobject -n storm-cluster
kubectl get hpa -n storm-cluster
```

## Custom Docker Images

All images live under `mr4x2/` on DockerHub. For K8s, use the `-k8s` tagged variants:

| Image | Notes |
|---|---|
| `mr4x2/nimbus-k8s:v2.2` | Includes autoscale JAR |
| `mr4x2/supervisor-k8s:v2.1` | |
| `mr4x2/zookeeper-k8s:v1.1` | |
| `mr4x2/stormexporter:v1.2.5` | Prometheus exporter (K8s uses older version than Docker Compose) |
| `mr4x2/mqtt-broker` | |
| `mr4x2/keda-controller:v1` | Custom KEDA external scaler |

## Persistent Storage (MySQL)

```bash
# PV uses hostPath — requires this directory to exist on the node
kubectl exec -it <node> -- mkdir -p /mnt/data
```
