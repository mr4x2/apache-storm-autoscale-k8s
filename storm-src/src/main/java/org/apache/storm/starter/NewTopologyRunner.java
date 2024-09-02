package org.apache.storm.starter;

import org.apache.storm.Config;
import org.apache.storm.StormSubmitter;
import org.apache.storm.generated.StormTopology;
import org.apache.storm.starter.metric.MetricsController;

public class NewTopologyRunner {
    public static void main(String[] args) throws Exception {
        Config conf = new Config();
        conf.setDebug(true);
        conf.setMaxTaskParallelism(4);
        conf.setNumWorkers(4);

        StormTopology topology = GithubCommitCountTopo.build();
        String topologyName = "github-counter1";
        StormSubmitter.submitTopology(topologyName, conf, topology);
        MetricsController metricsController = new MetricsController();
        metricsController.startMetrics("github-counter1", "email-counter");

    }
}
