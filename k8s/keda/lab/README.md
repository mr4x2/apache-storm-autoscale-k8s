**Step 1: Prerequisites**
- Kubernetes cluster with kubectl configured.
- Helm installed.
- KEDA installed (use Helm if not installed yet):

```cmd
helm repo add kedacore https://kedacore.github.io/charts
helm repo update
helm install keda kedacore/keda --namespace keda --create-namespace
```

**Install MQTT**

```cmd
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install rabbitmq bitnami/rabbitmq --namespace rabbitmq --create-namespace



root@bigdata-vm:~# echo "Username      : user"
Username      : user
root@bigdata-vm:~# echo "Password      : $(kubectl get secret --namespace rabbitmq rabbitmq -o jsonpath="{.data.rabbitmq-password}" | base64 -d)"
Password      : oYOGgoxLQwFN4EiK
root@bigdata-vm:~# echo "ErLang Cookie : $(kubectl get secret --namespace rabbitmq rabbitmq -o jsonpath="{.data.rabbitmq-erlang-cookie}" | base64 -d)"
ErLang Cookie : DcdDBZlKrTnLIeG9AParNY8VlvhaPPqG

```


**Build image**

```cmd
docker build -t mr4x2/worker:latest .
docker push mr4x2/worker:latest
```
sMkJWhgfVpvB0VWf
sohdixSWnzt3jULSAG2r4DqaA41HSZmz

