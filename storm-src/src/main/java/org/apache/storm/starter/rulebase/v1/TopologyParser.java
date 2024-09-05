package org.apache.storm.starter.rulebase.v1;

import org.apache.storm.starter.metric.ComponentMetricsCreator;

import java.io.*;
import java.util.HashMap;
import java.util.Map;

public class TopologyParser {


    private static String topologyName;
    private static Map<String, ComponentNode> spoutMap;
    private static Map<String, ComponentNode> boltMap;
    private static Map<String, Double> targetThroughput;

    //    Read input file which is included name of topology, component
    public static void readInput(String fileName) throws Exception {
        spoutMap = new HashMap<>();
        boltMap = new HashMap<>();

        // Use class loader to get the resource
        try (InputStream inputStream = TopologyParser.class.getClassLoader().getResourceAsStream(fileName);
             BufferedReader in = new BufferedReader(new InputStreamReader(inputStream))) {

            if (inputStream == null) {
                throw new FileNotFoundException("File not found in resources: " + fileName);
            }

            String line;
            String[] parts;
            ComponentNode source;
            ComponentNode destination;

            if ((line = in.readLine()) != null) {
                topologyName = line;
            } else {
                throw new Exception("Empty file: " + fileName);
            }

            while ((line = in.readLine()) != null) {
                if (!line.contains(" ")) {
                    throw new IllegalArgumentException("String '" + line + "' does not contain space");
                }

                parts = line.split(" ");

                if (parts.length != 2) {
                    throw new IllegalArgumentException("String '" + line + "' should contain exactly 2 vertices");
                }

                if (spoutMap.containsKey(parts[1])) {
                    destination = spoutMap.get(parts[1]);
                } else if (boltMap.containsKey(parts[1])) {
                    destination = boltMap.get(parts[1]);
                } else {
                    destination = new ComponentNode(new ComponentMetricsCreator(topologyName, parts[1]));

                    if (destination.getNode().getComponentType() == 1) {
                        boltMap.put(parts[1], destination);
                    } else if (destination.getNode().getComponentType() == 2) {
                        spoutMap.put(parts[1], destination);
                    }
                }

                if (spoutMap.containsKey(parts[0])) {
                    source = spoutMap.get(parts[0]);
                    source.addNeighbor(destination);
                } else if (boltMap.containsKey(parts[0])) {
                    source = boltMap.get(parts[0]);
                    source.addNeighbor(destination);
                } else {
                    source = new ComponentNode(new ComponentMetricsCreator(topologyName, parts[0]));
                    source.addNeighbor(destination);

                    if (source.getNode().getComponentType() == 1) {
                        boltMap.put(parts[0], source);
                    } else if (source.getNode().getComponentType() == 2) {
                        spoutMap.put(parts[0], source);
                    }
                }
            }
        }
    }

    // Read target each component
    public static void readTargetThroughput(String fileName) throws Exception {
        targetThroughput = new HashMap<String, Double>();

        // Use class loader to get the resource
        try (InputStream inputStream = TopologyParser.class.getClassLoader().getResourceAsStream(fileName);
             BufferedReader in = new BufferedReader(new InputStreamReader(inputStream))) {

            if (inputStream == null) {
                throw new FileNotFoundException("File not found in resources: " + fileName);
            }

            String line;
            String[] parts;

            while ((line = in.readLine()) != null) {
                if (!line.contains(" ")) {
                    throw new IllegalArgumentException("String '" + line + "' does not contain space");
                }

                parts = line.split(" ");
                targetThroughput.put(parts[0], Double.parseDouble(parts[1]));
            }
        }
    }


    public static void updateTopology() {

        for (String key : spoutMap.keySet()) {
            spoutMap.get(key).getNode().getComponentUpdater().updateMetrics();
        }

        for (String key : boltMap.keySet()) {
            boltMap.get(key).getNode().getComponentUpdater().updateMetrics();
        }
    }

    public static void initMetrics() throws Exception {

        updateTopology();
        Thread.sleep(10 * 1000);
        updateTopology();

    }


    public static void printTree(ComponentNode root) {
        System.out.println(root.getNode().getComponentId());
        for (ComponentNode leaf : root.getNeighbors()) {
            printTree(leaf);
        }
    }

    public static void main(String[] args) {
        try {

            if (args.length != 2) {
                System.out.println("Usage: TopologyParser <topology_filename> <throughput_target_filename");
                System.exit(1);
            }


            System.out.println("Reading topology configuration file");
            readInput(args[0]);
            System.out.println("Reading throughput configuration file");
            readTargetThroughput(args[1]);
            System.out.println("Initializing Metrics");
            initMetrics();

            FlowCheck flow = new FlowCheck(topologyName, spoutMap, boltMap, targetThroughput);

            while (true) {
                System.out.println("Wait for 30 sec");
                Thread.sleep(60 * 1000);

                System.out.println("Update topology stats");
                updateTopology();

                System.out.println("Check the flow");
                flow.initFlowCheck();

                if (flow.isRebalanced()) {
                    System.out.println("Wait to rebalance: 30sec");
                    Thread.sleep(60 * 1000);

                    initMetrics();

                    flow.rebalanceInit();
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void autoScale(String inputFile, String targetFile) {
        try {


            System.out.println("Reading topology configuration file");
            readInput(inputFile);
            System.out.println("Reading throughput configuration file");
            readTargetThroughput(targetFile);
            System.out.println("Initializing Metrics");
            initMetrics();

            FlowCheck flow = new FlowCheck(topologyName, spoutMap, boltMap, targetThroughput);

            while (true) {
                System.out.println("Wait for 30 sec");
                Thread.sleep(60 * 1000);

                System.out.println("Update topology stats");
                updateTopology();

                System.out.println("Check the flow");
                flow.initFlowCheck();

                if (flow.isRebalanced()) {
                    System.out.println("Wait to rebalance: 30sec");
                    Thread.sleep(60 * 1000);

                    initMetrics();

                    flow.rebalanceInit();
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

}
