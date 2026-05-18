# Aristo Algorithm Versions

Source: [vgolemis/aristo](https://github.com/vgolemis/aristo)

This document covers what changed across Aristo's four `rulebased` versions and how the version used in this repo (`rulebase/v1` in `storm-src/`) diverges from the original v1.

---

## Version Comparison

### v1 → v2

**Package:** `rulebased` → `rulebasedv2`

| Change | v1 | v2 |
|---|---|---|
| Metric reference | Spout metrics only | Tracks both spout and bolt metrics separately |
| `compareSpoutStats` increase threshold | >1% → return -1 | >5% → return -1 (less sensitive to improvement) |
| Latency check in `compareSpoutStats` | Yes (on both increase and decrease) | Removed entirely |
| Executor tracking | Not tracked separately | `executors = countThreads()` at init |
| Worker scaling formula | `(countThreads() + changes) / (cores * workers) > 2` | `(executors + changes) > (cores * workers)` |
| Pre-worker check | None | Checks if executors already exceed capacity before bolt inspection |
| `initSpoutCheck` | Inline in `initFlowCheck` | Returns `boolean`, caller decides |
| `checkNeeded` flag | No | Yes — skips bolt check if no spout is below target |
| Null-guard on queue.poll() | No | Yes — `if(bolt == null) return` |

---

### v2 → v3

**Package:** `rulebasedv2` → `rulebasedv3`

| Change | v2 | v3 |
|---|---|---|
| Output logging | None | `OutputWriter` writes config + metrics per rebalance |
| Config history | None | `TopologyConfiguration` + `List<TopologyConfiguration>` |
| Throughput/latency history | None | `histThroughput`, `histLatency` lists |
| Auto-terminate | No | Yes — kills topology when target is reached, writes history |
| Scale-down | No | Yes — if `changes == -1` (no bottleneck, total capacity < 0.6), removes a worker |
| `compareSpoutStats` | Static, no history | Accumulates `avgThroughput`, `avgLatency` per rebalance window |
| Bolt capacity check | `capacity` (avg) | `maxCapacity` (per-executor max) |
| `rebalanceInit` | Resets severity + config | Also writes current config to output file |
| `maxWorkers` | 4 | 4 (unchanged) |

---

### v3 → v4

**Package:** `rulebasedv3` → `rulebasedv4`

| Change | v3 | v4 |
|---|---|---|
| Primary metric | Spout `ackedRate` | **Bolt `ackedRate`** via `boltIndex` (e.g. `"split"`) |
| Target comparison | Per-spout in a loop | Single bolt identified by `boltIndex` |
| Severity map key | Per-spout | Single `boltIndex` key |
| `compareSpoutStats` | Uses `SpoutMetrics` | Uses `BoltMetrics` |
| BFS traversal | Recursive DFS | BFS using explicit `Queue` + `Set<visited>` |
| `maxWorkers` | 4 | **7** |
| Worker init | 1 | 1 (unchanged) |
| Output writer | On kill only | Also writes per-rebalance via `rebalanceInit` |

---

## Modifications Made to v1 for This Repo

The autoscaler in `storm-src/src/main/java/org/apache/storm/starter/rulebase/v1/` is based on Aristo v1 with the following changes:

### `FlowCheck.java`

| Parameter | Aristo v1 | This repo |
|---|---|---|
| `workers` (initial) | `1` | `2` |
| `maxWorkers` | `4` | `28` |
| Bolt capacity stop threshold | `> 0.8` | `> 0.7` |

The lower capacity threshold (`0.7`) means scaling triggers earlier — more aggressive than the original. The higher `maxWorkers` and starting worker count reflect the K8s environment where more supervisor pods are available.

### `TopologyParser.java`

| Aspect | Aristo v1 | This repo |
|---|---|---|
| File reading | `new FileReader(fileName)` — reads from filesystem path | `getClassLoader().getResourceAsStream(fileName)` — reads from JAR classpath |
| Input/target files | External files passed as args | Bundled inside JAR under `src/main/resources/` |

This change allows the JAR to be self-contained when deployed inside the Nimbus container — no need to separately copy input files.

### Topology configuration (`input.txt`, `target.txt`)

Aristo v1 was tested against a simple `FastWordCountTopology` (`spout → split → count`). This repo replaces it with the IoT smart home topology (`spout-data-iot-data → split-{1..120} → avg → sum/forecast`) with a target of 4000 msgs/sec.

---

## Metrics Collection Plan

### Target metrics for comparison
| Metric | Source |
|---|---|
| Throughput over time | Prometheus — `spouts_acked`, `spouts_complete_latency` |
| Latency over time | Prometheus — `spouts_complete_latency` |
| Executor count over time | Prometheus — `executors_total` |
| Worker count over time | Prometheus — `workers_total` |
| Rebalance count | OutputWriter file (per rebalance record) |
| Time to stabilize | OutputWriter file (timestamp delta) |

### Option 1 — Prometheus + OutputWriter (chosen)
Add `OutputWriter` and `TopologyConfiguration` (from Aristo v3/v4) to **both** autoscaler versions. Each rebalance writes a structured record: timestamp, worker count, executor counts, avg throughput, avg latency. Prometheus handles time-series view; output files handle summary stats and rebalance count.

**Current status:** Prometheus is already set up. `OutputWriter` is not yet added to either version — this is a pending task for both `rulebase/v1/` (current modified version) and the new `rulebase/aristo/` subdirectory.

### Option 2 — Prometheus only (future fallback)
Rely entirely on Grafana for all metrics. Rebalance events are inferred from step changes in `executors_total` and `workers_total`. No code changes needed. Less precise for rebalance count and time-to-stabilize — requires manual reading from graphs.

---

## Planned Experiments

### Experiment A — Algorithm comparison (active)
Both versions use KEDA for pod scaling. Only the Java executor autoscaler differs:
- Version A (current): modified Aristo v1 (`workers=2`, `maxWorkers=28`, threshold `0.7`)
- Version B (new): original Aristo v1 minimally adapted (`workers=1`, threshold `0.8`, `maxWorkers` matched to cluster)

Any throughput/latency difference is directly attributable to the algorithm parameters.

### Experiment B — Full system comparison (future)
- Version A: modified Aristo v1 + KEDA pod scaling
- Version B: original Aristo v1, executor scaling only, no KEDA

Compares two complete autoscaling philosophies. Note: two variables change simultaneously (algorithm + infrastructure), so results need careful interpretation.

---

## Key Conceptual Differences Across All Versions

| Capability | v1 | v2 | v3 | v4 |
|---|---|---|---|---|
| Scale up executors | ✓ | ✓ | ✓ | ✓ |
| Scale up workers | ✓ | ✓ | ✓ | ✓ |
| Scale down workers | ✗ | ✗ | ✓ | ✓ |
| Auto-terminate on target reached | ✗ | ✗ | ✓ | ✓ |
| Output logging | ✗ | ✗ | ✓ | ✓ |
| Config history tracking | ✗ | ✗ | ✓ | ✓ |
| Latency in severity | ✓ | ✗ | ✗ | ✗ |
| Null-safe queue poll | ✗ | ✓ | ✓ | ✓ |
| BFS traversal | ✗ | ✗ | ✗ | ✓ |
| Bolt-indexed monitoring | ✗ | ✗ | ✗ | ✓ |
