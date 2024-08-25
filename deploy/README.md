### How to run in multiple cluster


Run nimus and ui

```cmd
docker run -d -p 6622:6627 -p 8081:8081 --name storm-nimbus-ui mr4x2/nimbus:v2
```

Run zookeeper

```cmd
docker run --name zookeeper -d -p 2181:2181 mr4x2/zookeeper:v1
```

Run supervisor

```cmd
docker run -d -p 6622:6627 -p 6700-6703:6700-6703 --name storm-supervisor mr4x2/supervisor:v1
```


Run exporter
```cmd
docker run -d -p 8082:8082 -env-file storm_exporter.env --name storm-exporter mr4x2/stormexporter:v1
```
