package org.apache.storm.starter;

import org.apache.storm.generated.StormTopology;
import org.apache.storm.starter.bolt.EmailCounterBolt;
import org.apache.storm.starter.bolt.EmailExtractorBolt;
import org.apache.storm.starter.spout.CommitFeedListenerSpout;
import org.apache.storm.topology.TopologyBuilder;
import org.apache.storm.tuple.Fields;

public class GithubCommitCountTopo {

    public static StormTopology build() {
        TopologyBuilder builder = new TopologyBuilder();
        builder.setSpout("commit-feed-email", new CommitFeedListenerSpout(), 2).setNumTasks(2).setMaxTaskParallelism(250);
        builder.setBolt("email-extractor", new EmailExtractorBolt(), 2).shuffleGrouping("commit-feed-email").setNumTasks(4).setMaxTaskParallelism(250);
        builder.setBolt("email-counter", new EmailCounterBolt(), 2).fieldsGrouping("email-extractor", new Fields("email")).setNumTasks(2).setMaxTaskParallelism(250);
        return builder.createTopology();
    }

}
