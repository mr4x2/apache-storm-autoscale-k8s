package org.apache.storm.starter;

import org.apache.storm.Config;
import org.apache.storm.StormSubmitter;
import org.apache.storm.generated.StormTopology;

public class NewScaleTopology {
    public static void main(String[] args) throws Exception {
        Config conf = new Config();
        conf.setDebug(true);
        // conf.setMaxTaskParallelism(4);
        conf.setNumWorkers(4);

        StormTopology topology = GithubCommitCountTopo.build();
        String topologyName = "test-get-metric";
        StormSubmitter.submitTopology(topologyName, conf, topology);
    }
}
