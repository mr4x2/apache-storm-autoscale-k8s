# Dynamic Multi-Level Autoscale Apache Storm in Kubernetes


### How to run topology


### How to run autoscale program

```cmd
storm jar storm-src-1.0-SNAPSHOT.jar org.apache.storm.starter.rulebase.v1.TopologyParser input.txt target.txt
```

### How to apply topology

```cmd
storm jar Storm-IOTdata-1.0-SNAPSHOT-jar-with-dependencies.jar com.storm.iotdata.MainTopo
```

### TODO

**This is todo list must be done**
- [X] Smart autoscale
- [X] Skip autoscale if metric isn't collected