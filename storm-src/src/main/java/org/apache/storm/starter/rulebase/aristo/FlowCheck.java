package org.apache.storm.starter.rulebase.aristo;

import org.apache.storm.starter.metric.BoltMetrics;
import org.apache.storm.starter.metric.BoltMetricsUpdater;
import org.apache.storm.starter.metric.SpoutMetrics;
import org.apache.storm.starter.metric.SpoutMetricsUpdater;

import java.util.*;

/**
 * Original Aristo v1 FlowCheck — minimally adapted for the IoT smart-home topology.
 *
 * Adaptations from original (vgolemis/aristo rulebased/FlowCheck.java):
 *   - maxWorkers: 4 → 28  (infrastructure: matches K8s cluster size)
 *   - OutputWriter added for per-rebalance metrics recording
 *
 * Intentionally unchanged (algorithm parameters):
 *   - workers initial value: 1
 *   - Bolt capacity stop threshold: 0.8
 *   - compareSpoutStats thresholds: +1% improvement, -2% drop, 100% latency spike
 *   - Severity logic and maxSeverity: 2
 *   - Worker scaling formula: (countThreads() + changes) / (cores * workers) > 2
 */
public class FlowCheck {

    private String topologyName;
    private int moves;
    private int changes;
    private int cores;
    private int workers;
    private int maxWorkers;

    private static Map<String, ComponentNode> spoutMap;
    private static Map<String, ComponentNode> boltMap;
    private Map<String, Double> targetThroughput;

    private Map<String, SpoutMetrics> currentRootStats;
    private Map<String, SpoutMetrics> previousRootStats;
    private Map<String, Integer> severity;
    private int maxSeverity;

    private RebalanceMove previousConfig;
    private RebalanceMove currentConfig;

    private List<TopologyConfiguration> previousConfigs;
    private List<Double> histThroughput;
    private List<Double> histLatency;
    private Double avgThroughput;
    private Double avgLatency;
    private int count;

    private boolean rebalanced;

    private long start, stop;
    private OutputWriter writer;
    private TopologyConfiguration conf;


    public FlowCheck(String topologyName, Map<String, ComponentNode> spoutMap, Map<String, ComponentNode> boltMap, Map<String, Double> throughput) {

        this.topologyName = topologyName;

        moves = 0;
        changes = 0;
        cores = 2;
        workers = 1;        // original Aristo v1 value
        maxWorkers = 28;    // adapted: matches K8s cluster size (original was 4)

        this.spoutMap = spoutMap;
        this.boltMap = boltMap;
        this.targetThroughput = throughput;

        currentRootStats = new HashMap<>();
        previousRootStats = new HashMap<>();
        severity = new HashMap<>();

        for (String key : spoutMap.keySet()) {
            severity.put(key, 0);
            previousRootStats.put(key, new SpoutMetrics(((SpoutMetricsUpdater) spoutMap.get(key).getNode().getComponentUpdater()).getSpoutMetrics()));
        }
        maxSeverity = 2;

        previousConfig = new RebalanceMove();
        currentConfig = new RebalanceMove();

        previousConfigs = new ArrayList<>();
        Map<String, BoltMetrics> initBoltStats = new HashMap<>();
        for (String key : boltMap.keySet())
            initBoltStats.put(key, ((BoltMetricsUpdater) boltMap.get(key).getNode().getComponentUpdater()).getBoltMetrics());
        conf = new TopologyConfiguration(workers, previousRootStats, initBoltStats);
        previousConfigs.add(conf);

        histThroughput = new ArrayList<>();
        histLatency = new ArrayList<>();
        avgThroughput = 0d;
        avgLatency = 0d;
        count = 0;

        rebalanced = false;

        start = System.currentTimeMillis();
        writer = new OutputWriter(topologyName);
    }


    public static int countThreads() {
        int threads = 0;
        for (String key : spoutMap.keySet())
            threads += ((SpoutMetricsUpdater) spoutMap.get(key).getNode().getComponentUpdater()).getSpoutMetrics().getExecutors();
        for (String key : boltMap.keySet())
            threads += ((BoltMetricsUpdater) boltMap.get(key).getNode().getComponentUpdater()).getBoltMetrics().getExecutors();
        return threads;
    }


    public void rebalanceInit() throws Exception {
        for (String key : spoutMap.keySet()) {
            severity.put(key, 0);
            previousRootStats.put(key, new SpoutMetrics(((SpoutMetricsUpdater) spoutMap.get(key).getNode().getComponentUpdater()).getSpoutMetrics()));
        }

        moves++;
        previousConfig = currentConfig;
        currentConfig = new RebalanceMove();

        stop = System.currentTimeMillis();
        writer.write(conf, avgThroughput / count, avgLatency / count, stop - start);

        Map<String, BoltMetrics> currentBoltStats = new HashMap<>();
        for (String key : boltMap.keySet())
            currentBoltStats.put(key, ((BoltMetricsUpdater) boltMap.get(key).getNode().getComponentUpdater()).getBoltMetrics());
        conf = new TopologyConfiguration(workers, previousRootStats, currentBoltStats);
        previousConfigs.add(conf);

        histThroughput.add(avgThroughput / count);
        histLatency.add(avgLatency / count);

        avgThroughput = 0d;
        avgLatency = 0d;
        count = 0;

        rebalanced = false;
        start = System.currentTimeMillis();
    }


    // Original Aristo v1 compareSpoutStats — unchanged
    public static int compareSpoutStats(SpoutMetrics previous, SpoutMetrics current) {
        int severity = 0;

        System.out.println("throughput: " + previous.getAckedRate() + "-->" + current.getAckedRate());
        System.out.println("latency: " + previous.getCompleteLatency() + "-->" + current.getCompleteLatency());

        if (current.getAckedRate() > previous.getAckedRate()) {

            System.out.println("Relative increase: " + (current.getAckedRate() - previous.getAckedRate()) / previous.getAckedRate());

            if ((current.getAckedRate() - previous.getAckedRate()) / previous.getAckedRate() > 0.01)
                return -1;
            else
                severity++;

            if (previous.getCompleteLatency() > current.getCompleteLatency())
                severity--;

        } else {

            System.out.println("Relative decrease: " + (previous.getAckedRate() - current.getAckedRate()) / previous.getAckedRate());

            if ((previous.getAckedRate() - current.getAckedRate()) / previous.getAckedRate() > 0.02)
                severity++;

            if (current.getCompleteLatency() > previous.getCompleteLatency()) {
                if ((current.getCompleteLatency() - previous.getCompleteLatency()) / previous.getCompleteLatency() > 1)
                    severity++;
            }
        }

        return severity;
    }


    public void initFlowCheck() {
        changes = 0;

        for (String key : spoutMap.keySet()) {
            currentRootStats.put(key, ((SpoutMetricsUpdater) spoutMap.get(key).getNode().getComponentUpdater()).getSpoutMetrics());

            avgThroughput += currentRootStats.get(key).getAckedRate();
            avgLatency += currentRootStats.get(key).getCompleteLatency();
            count++;

            System.out.println("Spout: " + key + " target: " + targetThroughput.get(key) + " current: " + currentRootStats.get(key).getAckedRate());

            if (targetThroughput.get(key) > currentRootStats.get(key).getAckedRate())
                initSpoutCheck(spoutMap.get(key));
        }

        for (String key : spoutMap.keySet())
            previousRootStats.put(key, new SpoutMetrics(((SpoutMetricsUpdater) spoutMap.get(key).getNode().getComponentUpdater()).getSpoutMetrics()));

        try {
            if (changes > 0) {

                if ((countThreads() + changes) / (cores * workers) > 2) {
                    if (workers < maxWorkers) {
                        System.out.println("Added worker");
                        previousConfig.setWorkers(workers);
                        currentConfig.setWorkers(++workers);
                    }
                }

                System.out.println("Rebalance");
                currentConfig.commitRebalance(topologyName);
                rebalanced = true;
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }


    public void initSpoutCheck(ComponentNode root) {
        System.out.println("Checking: " + root.getNode().getComponentId());

        int tempSeverity = severity.get(root.getNode().getComponentId());
        System.out.println("Current severity: " + tempSeverity);

        tempSeverity += compareSpoutStats(previousRootStats.get(root.getNode().getComponentId()), currentRootStats.get(root.getNode().getComponentId()));
        System.out.println("New severity: " + tempSeverity);

        if (tempSeverity < 0)
            tempSeverity = 0;

        severity.put(root.getNode().getComponentId(), tempSeverity);

        if (tempSeverity < maxSeverity)
            return;

        PriorityQueue<ComponentNode> queue = new PriorityQueue<>(11, new BoltMetricsComparator());

        for (ComponentNode neighbor : root.getNeighbors())
            queue = recursiveInspect(neighbor, queue);

        // Original Aristo v1 capacity threshold: 0.8 (unchanged)
        ComponentNode bolt = queue.poll();
        BoltMetrics boltStats = ((BoltMetricsUpdater) bolt.getNode().getComponentUpdater()).getBoltMetrics();
        do {
            if (!currentConfig.getComponents().containsKey(bolt.getNode().getComponentId())) {
                System.out.println(boltStats.getId() + " capacity: " + boltStats.getCapacity());
                System.out.println(boltStats.getId() + " threads: " + boltStats.getExecutors() + "-->" + (boltStats.getExecutors() + 1));
                previousConfig.addComponent(bolt.getNode().getComponentId(), boltStats.getExecutors());
                currentConfig.addComponent(bolt.getNode().getComponentId(), boltStats.getExecutors() + 1);
                changes++;
            }

            bolt = queue.poll();
            if (bolt == null)
                return;
            boltStats = ((BoltMetricsUpdater) bolt.getNode().getComponentUpdater()).getBoltMetrics();
        }
        while (boltStats.getCapacity() > 0.8);   // original Aristo v1 threshold
    }


    public PriorityQueue<ComponentNode> recursiveInspect(ComponentNode bolt, PriorityQueue<ComponentNode> pq) {
        pq.add(bolt);
        for (ComponentNode neighbor : bolt.getNeighbors())
            pq = recursiveInspect(neighbor, pq);
        return pq;
    }


    public boolean isRebalanced() {
        return rebalanced;
    }

    public void setRebalanced(boolean rebalanced) {
        this.rebalanced = rebalanced;
    }
}
