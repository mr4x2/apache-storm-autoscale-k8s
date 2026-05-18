# Java Rule-Based Autoscaler

Located in `storm-src/src/main/java/org/apache/storm/starter/`.

## Purpose

Runs inside the Nimbus container as a long-lived process. Monitors Storm topology metrics and calls Storm's `rebalance` API to adjust **executor counts** (threads) per bolt/spout, and **worker counts**, based on throughput and capacity rules.

## How to Run

```bash
docker exec -it nimbus bash
cd /opt/storm/lib/
storm jar storm-autoscale-1.0.jar org.apache.storm.starter.rulebase.v1.TopologyParser input.txt target.txt
```

The two resource files (`input.txt`, `target.txt`) are bundled inside the JAR from `storm-src/src/main/resources/`.

## Input Files

### `input.txt` — Topology DAG
```
iot-smarthome                       ← topology name (first line)
spout-data-iot-data split-1         ← edge: source destination
spout-data-iot-data split-5
...
split-1 avg-1
avg-1 sum-1
avg-1 forecast-1
...
```

### `target.txt` — Throughput targets
```
spout-trigger 4000
spout-data-iot-data 4000
```
Values are in messages/second (acked tuples per second).

## Class Structure

```
metric/
  ComponentMetricsCreator       ← Connects to Nimbus Thrift, detects component type
  ComponentMetricsUpdaterInterface  ← Interface: updateMetrics() + printMetrics()
  BoltMetricsUpdater            ← Fetches bolt stats via ComponentPageInfo
  SpoutMetricsUpdater           ← Fetches spout stats via ComponentPageInfo
  BoltMetrics                   ← POJO: capacity, latency, rates, executor count
  SpoutMetrics                  ← POJO: ackedRate, completeLatency, executor count
  ComponentUpdater              ← Delegates to bolt/spout updater
  MetricsController             ← Standalone debug main (prints metrics loop)

rulebase/v1/
  TopologyParser                ← Entry point: reads input, runs main loop
  FlowCheck                     ← Core autoscale decision logic
  RebalanceMove                 ← Wraps RebalanceOptions, calls nimbus.rebalance()
  ComponentNode                 ← DAG node wrapping ComponentMetricsCreator + neighbors
  BoltMetricsComparator         ← Comparator: descending by bolt capacity
```

## Algorithm

### Main Loop (`TopologyParser.main`)

1. Parse `input.txt` → build `spoutMap` and `boltMap` of `ComponentNode` objects
2. Parse `target.txt` → `targetThroughput` map
3. Call `initMetrics()` — update metrics twice with 10s gap (warm-up)
4. Create `FlowCheck`
5. Every **30 seconds**:
   - `updateTopology()` — fetch fresh metrics for all components
   - `flow.initFlowCheck()` — run scaling decision
   - If rebalance was issued: wait 30s, re-init metrics, reset state

### Scaling Decision (`FlowCheck.initFlowCheck`)

For each spout:
1. Compare `currentAckedRate` vs `targetThroughput`
2. If below target: call `initSpoutCheck()`

`compareSpoutStats()` returns a severity delta:
- `-1` (good): throughput increased >1% → severity resets toward 0
- `+1` (warn): throughput dropped >2%, or latency doubled
- `+2` (critical): both throughput drop and latency spike

`initSpoutCheck()`:
1. Accumulate severity; if `severity < 2` (threshold), return — wait for more evidence
2. At `severity >= 2`: traverse downstream DAG, build a **max-heap** of bolts by `capacity`
3. Pop bolts in order; for each with `capacity > 0.7`: add 1 executor, record in `currentConfig`
4. Stop when the next bolt has `capacity <= 0.7`

Worker scaling (after executor changes):
```java
if ((countThreads() + changes) / (cores * workers) > 2 && workers < maxWorkers)
    workers++;  // maxWorkers = 28, cores = 2 (hardcoded)
```

### Applying Changes (`RebalanceMove.commitRebalance`)

Calls `nimbus.rebalance(topologyName, RebalanceOptions)` with:
- `set_num_executors(Map<String, Integer>)` — per-component executor counts
- `set_num_workers(int)` — total workers (only if worker was added)
- `set_wait_secs(0)` — immediate rebalance

## Metrics Collection Detail

Both `BoltMetricsUpdater` and `SpoutMetricsUpdater` call `client.getComponentPageInfo(topologyId, componentId, "600", false)`, fetching stats over a **600-second window**.

For bolts, per-executor stats are aggregated:
- `capacity = sum(executor_capacity) / numExecutors` (average)
- `maxCapacity = max(executor_capacity)`
- `processLatency = weighted avg by acked count`
- `executeLatency = weighted avg by executed count`
- Rates (`ackedRate`, `executeRate`, etc.) = total / 600

## Build

```bash
cd storm-src
mvn package
# Output: target/storm-src-1.0-SNAPSHOT.jar
```

Maven dependencies: `storm-core:2.6.2`, `storm-client:2.6.2`, Java 11.
