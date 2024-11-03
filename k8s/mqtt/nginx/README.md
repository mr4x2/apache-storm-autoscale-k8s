### How to run forward port nginx to mqtt pod in k8s cluster

```cmd
docker run -d -p 1883:1883 -v config/mqtt.conf:/etc/nginx/nginx.conf --name nginx-mqtt nginx
```