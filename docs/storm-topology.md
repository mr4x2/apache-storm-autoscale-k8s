# Storm Topology

## Topology Name

`iot-smarthome`

## DAG Structure

The topology processes time-windowed IoT sensor data (energy usage) from a single MQTT spout, fanning out to 8 time-window branches.

```
spout-data-iot-data
  ├── split-1   → avg-1   → sum-1    / forecast-1
  ├── split-5   → avg-5   → sum-5    / forecast-5
  ├── split-10  → avg-10  → sum-10   / forecast-10
  ├── split-15  → avg-15  → sum-15   / forecast-15
  ├── split-20  → avg-20  → sum-20   / forecast-20
  ├── split-30  → avg-30  → sum-30   / forecast-30
  ├── split-60  → avg-60  → sum-60   / forecast-60
  └── split-120 → avg-120 → sum-120  / forecast-120
```

Numbers represent time windows in minutes. Each branch computes rolling average, sum, and forecast for that window length.

## Throughput Targets

| Component | Target (msgs/sec) |
|---|---|
| `spout-data-iot-data` | 4000 |
| `spout-trigger` | 4000 |

These targets are read by the Java autoscaler from `target.txt`.

## Data Source

CSV sensor data from smart home energy monitors (format: `id,timestamp,value,...`). Published via MQTT to topic `iot-data`. The MQTT publisher (`k8s/mqtt/publisher/index.js`) reads CSV files and publishes at configurable speed.

## Storm Configuration

Each supervisor node provides **4 worker slots** (ports 6700–6703).

Key topology parameters (from `config/storm-nimbus.yaml`):
- `topology.workers: 1` (default; autoscaler increases this)
- `topology.builtin.metrics.bucket.size.secs: 60`
- `supervisor.memory.capacity.mb: 4096`
- `supervisor.cpu.capacity: 400`

## Topology JAR

The topology source code (`com.storm.iotdata.MainTopo`) lives in the **core project repository**: [fimocode/stormsmarthome](https://github.com/fimocode/stormsmarthome). See [`docs/related-projects.md`](related-projects.md) for full details on its components and build steps.

The built JAR must be placed at:

```
storm-src/target/Storm-IOTdata-1.0-SNAPSHOT-jar-with-dependencies.jar
```

Docker Compose mounts this into nimbus as `Storm-IOTdata-1.0.jar`.

## Autoscaler Input Files

The autoscaler reads the topology structure from resource files bundled in `storm-src/src/main/resources/`:

- `input.txt` — edge list defining the DAG (first line = topology name)
- `target.txt` — per-spout throughput targets

These files are embedded in the autoscaler JAR at build time. To change the topology structure or targets, edit these files and rebuild with `mvn package`.
