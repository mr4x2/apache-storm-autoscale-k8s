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


### Train

**Ex1**
Objective: Create a basic Storm topology that reads sentences, splits them into words, and counts the occurrences of each word.
Steps:
Create a Spout: Implement a spout that emits sentences.
Create a Bolt: Implement a bolt that splits the sentences into words.
Create another Bolt: Implement a second bolt that counts the occurrences of each word.
Topology: Wire the spout and bolts together in a topology and run it.


Key insight

```java

public class SplitWord extends BaseBasicBolt {
    @Override
    public void execute(Tuple tuple, BasicOutputCollector basicOutputCollector) {
        String sentence = tuple.getString(0);
        for (String word: sentence.split("\\s+")) {
            basicOutputCollector.emit(new Values(word, 1)); // it will send tuple like(word,1)
            System.out.println("Log bolt SplitSentence " + word);
        }
    }

    @Override
    public void declareOutputFields(OutputFieldsDeclarer outputFieldsDeclarer) {
        outputFieldsDeclarer.declare(new Fields("word", "count")); // this is name field in tuple will be sent (word, count)
    }
}

```


```java
// when i catch message like

String word = tuple.getString(0);
int numCount = tuple.getInteger(1);
System.out.println("Received word: " + word + " with count: " + numCount);
```

```cmd
# log in supervisor is
2024-08-23 16:14:17.319 o.a.s.s.b.CountWord Thread-17-wordCount-executor[13, 13] [INFO] Received word: a with count: 1
```

So how they catch tuple?

Reason is config in Topology between 2 bolt to get tuple

```java
builder.setBolt("split", new SplitWord(), 3).shuffleGrouping("spout");
builder.setBolt("wordCount", new CountWord(), 3).fieldsGrouping("split", new Fields("word"));
```


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

- [ ] Write config to yaml
- [ ] Smart autoscale
- [X] Skip autoscale if metric isn't collected