package org.apache.storm.starter.rulebase.v1;
import org.apache.storm.starter.metric.*;

import java.util.*;


public class FlowCheck {


    private String  topologyName;
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

    private boolean rebalanced;



    public FlowCheck(String topologyName, Map<String, ComponentNode> spoutMap, Map<String, ComponentNode> boltMap, Map<String, Double> throughput) {

        this.topologyName = topologyName;

        moves = 0;
        changes = 0;
        cores = 2;
        workers = 1;
        maxWorkers = 4;

        this.spoutMap = spoutMap;
        this.boltMap = boltMap;

        this.targetThroughput = throughput;


        this.currentRootStats = new HashMap<String, SpoutMetrics>();

        previousRootStats = new HashMap<String, SpoutMetrics>();
        severity = new HashMap<String, Integer>();
        for (String key : spoutMap.keySet()) {
            severity.put(key, 0);
            previousRootStats.put(key, new SpoutMetrics(((SpoutMetricsUpdater)spoutMap.get(key).getNode().getComponentUpdater()).getSpoutMetrics()));
        }
        maxSeverity = 2;

        previousConfig = new RebalanceMove();
        currentConfig = new RebalanceMove();

        rebalanced = false;
    }


    public static int countThreads() {
//    1 thread = 1 executor
        int threads = 0;

        for (String key : spoutMap.keySet()) {
            threads += ((SpoutMetricsUpdater)spoutMap.get(key).getNode().getComponentUpdater()).getSpoutMetrics().getExecutors();
        }

        for (String key : boltMap.keySet()) {
            threads += ((BoltMetricsUpdater)boltMap.get(key).getNode().getComponentUpdater()).getBoltMetrics().getExecutors();
        }

        return threads;
    }


    public void rebalanceInit() throws Exception{

        for (String key : spoutMap.keySet()) {
            severity.put(key, 0);
            previousRootStats.put(key, new SpoutMetrics(((SpoutMetricsUpdater)spoutMap.get(key).getNode().getComponentUpdater()).getSpoutMetrics()));
        }

        moves++;
        previousConfig = currentConfig;
        currentConfig = new RebalanceMove();

        rebalanced = false;


    }


    public static int compareSpoutStats(SpoutMetrics previous, SpoutMetrics current) {
        int severity = 0;

        System.out.println("throughput: " + previous.getAckedRate() + "-->" + current.getAckedRate());
        System.out.println("latency: " + previous.getCompleteLatency() + "-->" + current.getCompleteLatency());

        if(current.getAckedRate() > previous.getAckedRate()) {

            System.out.println("Relative increase: " + (current.getAckedRate() - previous.getAckedRate()) / previous.getAckedRate());

            if((current.getAckedRate() - previous.getAckedRate()) / previous.getAckedRate() > 0.01)
                return -1;
            else
                severity++;

            if(previous.getCompleteLatency() > current.getCompleteLatency()) {
                severity--;
            }

        }
        else {

            System.out.println("Relative decrease: " + (previous.getAckedRate() - current.getAckedRate()) / previous.getAckedRate());

            if((previous.getAckedRate() - current.getAckedRate()) / previous.getAckedRate() > 0.02)
                severity++;

            if(current.getCompleteLatency() > previous.getCompleteLatency()) {
                if((current.getCompleteLatency() - previous.getCompleteLatency()) / previous.getCompleteLatency() > 1)
                    severity++;
            }
        }

        return severity;

    }



    public void initFlowCheck() {
        changes = 0;

        for (String key : spoutMap.keySet()) {

            currentRootStats.put(key, ((SpoutMetricsUpdater)spoutMap.get(key).getNode().getComponentUpdater()).getSpoutMetrics());
            System.out.println("Spout: " + key + " target throughput: " + targetThroughput.get(key) + " current throughput: " + currentRootStats.get(key).getAckedRate());

            if(targetThroughput.get(key) > currentRootStats.get(key).getAckedRate()) {

                initSpoutCheck(spoutMap.get(key));

            }
        }

        //TODO if needed keep history stats when replacing in previous hashmap
        for (String key : spoutMap.keySet())
            previousRootStats.put(key, new SpoutMetrics(((SpoutMetricsUpdater)spoutMap.get(key).getNode().getComponentUpdater()).getSpoutMetrics()));


        try {
            if (changes > 0) {

                if ((countThreads() + changes) / (cores * workers) > 2) {
                    if(workers < maxWorkers) {

                        System.out.println("Added worker");
                        previousConfig.setWorkers(workers);
                        currentConfig.setWorkers(++workers);
                    }
                }

                System.out.println("Rebalance");
                currentConfig.commitRebalance(topologyName);

                rebalanced = true;
            }
        }
        catch(Exception e) {
            e.printStackTrace();
        }
    }

    public void initSpoutCheck(ComponentNode root){
        System.out.println("Checking: " + root.getNode().getComponentId());

        int tempSeverity = severity.get(root.getNode().getComponentId());

        System.out.println("Current severity: " + tempSeverity);

        tempSeverity += compareSpoutStats(previousRootStats.get(root.getNode().getComponentId()) , currentRootStats.get(root.getNode().getComponentId()));
        System.out.println("New severity: " + tempSeverity);

        if(tempSeverity < 0)
            tempSeverity = 0;

        severity.put(root.getNode().getComponentId(), tempSeverity);

        if (tempSeverity < maxSeverity)
            return;


        //put the bolts in a priority queue based on capacity
        PriorityQueue<ComponentNode> queue = new PriorityQueue<ComponentNode>(11, new BoltMetricsComparator());

        for (ComponentNode neighbor : root.getNeighbors()) {
            //inspectFlow(neighbor);
            queue = recursiveInspect(neighbor, queue);
        }


        //iterate through the queue while the capacity is greater than 0.8
        //if none of the bolts have capacity problem then we add a thread to the bolt with the biggest one (prediction that there is a [potential bottleneck)
        ComponentNode bolt = queue.poll();
        BoltMetrics boltStats = ((BoltMetricsUpdater) bolt.getNode().getComponentUpdater()).getBoltMetrics();
        do {

            if (!currentConfig.getComponents().containsKey(bolt.getNode().getComponentId())) {
                System.out.println(boltStats.getId() + " capacity: " + boltStats.getCapacity());
                System.out.println(boltStats.getId() + " threads: " + boltStats.getExecutors() + "-->" + (boltStats.getExecutors()+1));
                previousConfig.addComponent(bolt.getNode().getComponentId(), boltStats.getExecutors());
                currentConfig.addComponent(bolt.getNode().getComponentId(), boltStats.getExecutors() + 1);
                changes++;
            }

            bolt = queue.poll();
            boltStats = ((BoltMetricsUpdater) bolt.getNode().getComponentUpdater()).getBoltMetrics();
        }
        while(boltStats.getCapacity() > 0.8 );


    }


    public PriorityQueue<ComponentNode> recursiveInspect(ComponentNode bolt, PriorityQueue<ComponentNode> pq) {

        pq.add(bolt);

        for (ComponentNode neighbor : bolt.getNeighbors()) {
            pq = recursiveInspect(neighbor, pq);
        }

        return pq;
    }


    public void inspectFlow(ComponentNode bolt){

        BoltMetrics boltStats = ((BoltMetricsUpdater)bolt.getNode().getComponentUpdater()).getBoltMetrics();

        if(boltStats.getCapacity() > 0.9 && !currentConfig.getComponents().containsKey(bolt.getNode().getComponentId())) {
            System.out.println("Added Thread " + boltStats.getId());
            previousConfig.addComponent(bolt.getNode().getComponentId(), boltStats.getExecutors());
            currentConfig.addComponent(bolt.getNode().getComponentId(), boltStats.getExecutors()+1);
            changes++;
        }

        for (ComponentNode neighbor : bolt.getNeighbors()) {
            inspectFlow(neighbor);
        }

    }

    public boolean isRebalanced() {
        return rebalanced;
    }

    public void setRebalanced(boolean rebalanced) {
        this.rebalanced = rebalanced;
    }
}

