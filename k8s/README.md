# Apache Storm on Kubernetes

Full deployment guide: [`docs/deployment-k8s.md`](../docs/deployment-k8s.md)

## Quick Deploy

```bash
# 1. Create local cluster
kind create cluster --config kind-k8s-cluster.yml

# 2. Deploy Storm
kubectl create -f storm-ns.yml
kubectl create -f storm-svc.yml
kubectl create -f storm-pv.yml
kubectl create -f storm-pvc.yml
kubectl create -f storm-k8s.yml
```

After deployment, create the `/mnt/data` directory on the node (required for MySQL PersistentVolume):

```bash
mkdir -p /mnt/data
```

## Deploy Monitoring

```bash
kubectl apply -f monitoring/prom-grafana/configMap/
kubectl apply -f monitoring/prom-grafana/kubelet-metrics/
kubectl apply -f monitoring/prom-grafana/monitoring-pv.yml
kubectl apply -f monitoring/prom-grafana/monitoring-pvc.yml
kubectl apply -f monitoring/prom-grafana/prometheus-deployment.yml
kubectl apply -f monitoring/prom-grafana/monitoring-svc.yml
kubectl apply -f monitoring/prom-grafana/svc/
kubectl apply -f monitoring/storm-exporter/
```

## Deploy KEDA Autoscaler

```bash
kubectl apply -f keda/custom-metrics/autoscale-controller-deployment.yml
kubectl apply -f keda/autoscale-keda.yaml
```

## Custom Images

| Image | Version |
|---|---|
| `mr4x2/nimbus-k8s` | `v2.2` (includes autoscale JAR) |
| `mr4x2/supervisor-k8s` | `v2.1` |
| `mr4x2/zookeeper-k8s` | `v1.1` |
| `mr4x2/stormexporter` | `v1.2.5` |
| `mr4x2/mqtt-broker` | latest |
| `mr4x2/keda-controller` | `v1` |

## External Access

| Service | NodePort |
|---|---|
| Storm UI | `30001` |
| MQTT Broker | `30002` |
