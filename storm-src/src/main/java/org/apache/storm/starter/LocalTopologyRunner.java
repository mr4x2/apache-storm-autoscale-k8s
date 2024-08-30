package org.apache.storm.starter;

import org.apache.storm.Config;
import org.apache.storm.generated.StormTopology;
import org.apache.storm.LocalCluster;

public class LocalTopologyRunner {
    public static void main(String[] args) throws Exception {
        Config config = new Config();

        StormTopology topology = HeatMapTopologyBuilder.build();

        LocalCluster localCluster = new LocalCluster();
        localCluster.submitTopology("local-heatmap", config, topology);


    }
}
