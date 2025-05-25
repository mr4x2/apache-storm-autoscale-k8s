[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/mr4x2/apache-storm-autoscale-k8s)

# Dynamic Multi-Level Autoscale Apache Storm in Kubernetes


### How to run topology

```cmd
docker compose up -d
```

### How to apply topology

```cmd
docker exec -it nimbus bash
cd /opt/storm/lib/
storm jar Storm-IOTdata-1.0.jar com.storm.iotdata.MainTopo
```


### How to run autoscale program

```cmd
docker exec -it nimbus bash
cd /opt/storm/lib/
storm jar storm-autoscale-1.0.jar org.apache.storm.starter.rulebase.v1.TopologyParser input.txt target.txt
```
