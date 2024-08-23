package org.apache.storm.starter.spout;

import org.apache.storm.spout.SpoutOutputCollector;
import org.apache.storm.task.TopologyContext;
import org.apache.storm.topology.OutputFieldsDeclarer;
import org.apache.storm.topology.base.BaseRichSpout;
import org.apache.storm.tuple.Fields;
import org.apache.storm.tuple.Values;
import org.apache.storm.utils.Utils;

import java.util.Map;
import java.util.Random;
import java.util.UUID;

public class RandomSentenceSpout extends BaseRichSpout {
    SpoutOutputCollector collector;
    Random random;


    @Override
    public void open(Map conf, TopologyContext context, SpoutOutputCollector collector) {
        this.collector = collector;
        this.random = new Random();
    }

    @Override
    public void nextTuple() {
        Utils.sleep(10);
        String[] sentences = new String[]{
                sentence("the cow jumped over the moon"), sentence("an apple a day keeps the doctor away"),
                sentence("four score and seven years ago"),
                sentence("snow white and the seven dwarfs"), sentence("i am at two with nature")
        };
        final String sentence = sentences[random.nextInt(sentences.length)];


        this.collector.emit(new Values(sentence), UUID.randomUUID());
    }

    protected String sentence(String input) {
        return input;
    }

    @Override
    public void ack(Object id) {
    }

    @Override
    public void fail(Object id) {
    }

    @Override
    public void declareOutputFields(OutputFieldsDeclarer declarer) {
        declarer.declare(new Fields("word"));
    }
}
