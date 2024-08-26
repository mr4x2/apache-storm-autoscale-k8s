package org.apache.storm.starter;

import org.apache.storm.Config;
import org.apache.storm.starter.bolt.EmailCounterBolt;
import org.apache.storm.starter.bolt.EmailExtractorBolt;
import org.apache.storm.starter.spout.CommitFeedListenerSpout;
import org.apache.storm.topology.ConfigurableTopology;
import org.apache.storm.topology.TopologyBuilder;
import org.apache.storm.tuple.Fields;

public class GithubCommitCountTopo extends ConfigurableTopology {

    public static void main(String[] args){
        ConfigurableTopology.start(new GithubCommitCountTopo(), args);
    }
    @Override
    protected int run(String[] args) throws Exception {
        TopologyBuilder builder = new TopologyBuilder();
        builder.setSpout("commit-feed-email", new CommitFeedListenerSpout(), 3);
        builder.setBolt("email-extractor", new EmailExtractorBolt(), 3).shuffleGrouping("commit-feed-email");
        builder.setBolt("email-counter", new EmailCounterBolt(),3).fieldsGrouping("email-extractor", new Fields("email"));

        Config conf = new Config();
        conf.setDebug(true);
        conf.setMaxTaskParallelism(4);

        String topologyName = "github-counter";
        conf.setNumWorkers(4);

        if (args != null && args.length >0){
            topologyName = args[0];
        }
        return submit(topologyName, conf, builder);
    }
}
