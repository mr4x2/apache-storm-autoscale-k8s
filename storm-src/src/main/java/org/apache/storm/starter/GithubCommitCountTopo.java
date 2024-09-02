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
        builder.setSpout("commit-feed-email", new CommitFeedListenerSpout(), 1);
        builder.setBolt("email-extractor", new EmailExtractorBolt(), 1).shuffleGrouping("commit-feed-email");
        builder.setBolt("email-counter", new EmailCounterBolt(), 1).fieldsGrouping("email-extractor", new Fields("email"));
        return builder.createTopology();
    }

}
