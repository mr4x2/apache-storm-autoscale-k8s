## How to expose kubelet metrics to prometheus with beginer


### RBAC
```cmd
kubectl create -f kube-cluster-role-binding.yml

kubectl create -f kube-services-account.yml

kubectl create -f metrics-cluster-role.yml

kubectl create -f pod-test-curl.yml
```

Link serviceAccount with prometheus-metrics-scraper-sa in prometheus



```yaml
spec:
    serviceAccount: prometheus-metrics-scraper-sa
    containers:
    - name: prometheus
```

Add ip node which is worker node or master node to config map

```yaml
 - job_name: 'kubelet-static-resource'
    scheme: https
    metrics_path: /metrics/resource
    tls_config:
      insecure_skip_verify: true  # Use with caution; prefer proper TLS in production
    bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
    static_configs:
      - targets:
          - 172.18.0.3:10250
          - 172.18.0.2:10250  # Replace with your actual target IP and port

  - job_name: 'kubelet-static-cadvisor'
    scheme: https
    metrics_path: /metrics/cadvisor
    tls_config:
      insecure_skip_verify: true  # Use with caution; prefer proper TLS in production
    bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
    static_configs:
      - targets:
          - 172.18.0.3:10250
          - 172.18.0.2:10250
```

create a pod to curl show metrics

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: metrics-scraper
  namespace: storm-cluster
spec:
  serviceAccount: prometheus-metrics-scraper-sa
  containers:
  - command:
    - tail
    - -f
    - /dev/null
    image: alpine/curl
    name: metrics-scraper
    resources: {}
  dnsPolicy: ClusterFirst
  restartPolicy: Always
```


```cmd
kubectl create -f pod-test-curl.yml


curl -k \
-H "Authorization: Bearer $(cat /var/run/secrets/kubernetes.io/serviceaccount/token)"  \
https://10.1.0.90:10250/metrics/cadvisor


curl -k \
-H "Authorization: Bearer $(cat /var/run/secrets/kubernetes.io/serviceaccount/token)"  \
https://10.1.0.90:10250/metrics/resource
```