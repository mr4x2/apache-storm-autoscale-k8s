package org.apache.storm.starter;

import org.apache.storm.Config;
import org.apache.storm.StormSubmitter;
import org.apache.storm.generated.StormTopology;
import org.apache.storm.starter.rulebase.v1.TopologyParser;

public class NewScaleTopology {
    public static void main(String[] args) throws Exception {
        Config conf = new Config();
        conf.setDebug(true);
        conf.setMaxTaskParallelism(4);
        conf.setNumWorkers(4);

        StormTopology topology = GithubCommitCountTopo.build();
        String topologyName = "test-scale-github-counter";
        StormSubmitter.submitTopology(topologyName, conf, topology);
    }
}
