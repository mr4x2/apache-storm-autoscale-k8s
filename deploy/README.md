### How to run in multiple cluster


Run nimus and ui

```cmd
docker run -d --net host --name storm-nimbus-ui mr4x2/nimbus-ui:v1
```

Run zookeeper

```cmd
docker run --name zookeeper -d --net host mr4x2/zookeeper:v1
```

Run supervisor

```cmd
docker run -d --net host --name storm-supervisor mr4x2/supervisor:v3
```


Run exporter
```cmd
docker run -d -p 8082:8082 -env-file storm_exporter.env --name storm-exporter mr4x2/stormexporter:v1
```
