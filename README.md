# train-with-storm


### How to run topology

```cmd
docker cp target/storm-src-1.0-SNAPSHOT.jar nimbus:/

docker exec -it bash nimbus

storm jar /storm-src-1.0-SNAPSHOT.jar org.apache.storm.starter.TopologyClassName

```

### How to debug

```cmd
docker exec -it supervisor bash
cat logs/workers-artifacts/word-count-v2-3-1724257800/6700/worker.log
```