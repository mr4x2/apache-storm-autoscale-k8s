package org.apache.storm.starter;

import org.apache.storm.Config;
import org.apache.storm.starter.bolt.CountWord;
import org.apache.storm.starter.bolt.SplitWord;
import org.apache.storm.starter.spout.RandomStringSpout;
import org.apache.storm.topology.ConfigurableTopology;
import org.apache.storm.topology.TopologyBuilder;
import org.apache.storm.tuple.Fields;

public class WordCountTopology extends ConfigurableTopology {
    public static void main(String[] args) {
        ConfigurableTopology.start(new WordCountTopology(), args);
    }

    @Override
    protected int run(String[] strings) {
        TopologyBuilder builder = new TopologyBuilder();
        builder.setSpout("spout", new RandomStringSpout(), 3);
        builder.setBolt("split", new SplitWord(), 3).shuffleGrouping("spout");
        builder.setBolt("wordCount", new CountWord(), 3).fieldsGrouping("split", new Fields("word"));

        Config conf = new Config();
        conf.setDebug(true);
        conf.setMaxTaskParallelism(4);

        String topologyName = "word-count-by-Tu";

        conf.setNumWorkers(4);

        if (strings != null && strings.length > 0) {
            topologyName = strings[0];
        }
        return submit(topologyName, conf, builder);
    }
}
