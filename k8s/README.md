### How to run apache storm in k8s


mr4x2/nimbus-k8s:v1.1

mr4x2/supervisor-k8s:v1.1

mr4x2/zookeeper-k8s:v1.1

TODO: k8s for mqtt broker and mqtt publisher -> Done, deployment monitoring 

sizing mqtt broker -> phù hợp, dựng cả cụm monitoring, mqtt ko thấy tải lên??



mkdir -p /mnt/data


tìm hiểu tại sao processing time lớn + độ trễ cao

Số spout luôn là 1 thì sẽ ko gây processing cao 

Tăng tất cả task của storm lên -> processing rất cao , không khác gì tăng task của spout, nghi ngờ ko đủ resource để scale -> scale đủ worker thì oke luôn


mr4x2/nimbus-k8s:v1.2.2, worker tăng thêm -> giảm latency




Ha con mqtt thôi -> xem có tăng tải ko 

Thực ra là con spout nữa


-> Tìm hiểu keda -> oke





### Mop triển khai storm k8s

**Tạo k8s cluster**

```cmd
cd k8s/

kind create cluster --config kind-k8s-cluster.yml
```

**Install storm**


```cmd
cd k8s/

kubectl create -f storm-ns.yml

kubectl create -f storm-svc.yml

kubectl create -f storm-pv.yml

kubectl create -f storm-pvc.yml

kubectl create -f storm-k8s.yml
```

create reverse proxy for mqtt broker

```cmd

cd /broker/
# edit vm ip 
vim nginx/config/mqtt.conf

cd nginx/

docker compose up -d
```






