package org.apache.storm.starter.spout;

import org.apache.storm.spout.SpoutOutputCollector;
import org.apache.storm.task.TopologyContext;
import org.apache.storm.topology.OutputFieldsDeclarer;
import org.apache.storm.topology.base.BaseRichSpout;

import java.util.Map;
import java.util.Random;
import java.util.UUID;

import org.apache.storm.tuple.Fields;
import org.apache.storm.tuple.Values;
import org.apache.storm.utils.Utils;

public class RandomStringSpout extends BaseRichSpout {
    SpoutOutputCollector collector;
    Random random;

    protected String sentence(String input) {
        return input;
    }

    @Override
    public void open(Map<String, Object> map, TopologyContext topologyContext, SpoutOutputCollector spoutOutputCollector) {
        this.collector = spoutOutputCollector;
        this.random = new Random();
    }

    @Override
    public void nextTuple() {
        Utils.sleep(10);
        String[] sentences = new String[]{
                sentence("Implement a spout that emits sentences"), sentence("Create another Bolt: Implement a second bolt that counts the occurrences of each word."),
                sentence("Create a Spout: Implement a spout that emits numbers."),
                sentence("Create a Filter Bolt: Implement a bolt that filters out even numbers."), sentence("Create a Filter Bolt: Implement a bolt that filters out even numbers.")
        };
        final String sentence = sentences[random.nextInt(sentences.length)];

        this.collector.emit(new Values(sentence), UUID.randomUUID());
    }

    @Override
    public void ack(Object id) {

    }

    @Override
    public void fail(Object id) {
    }

    @Override
    public void declareOutputFields(OutputFieldsDeclarer outputFieldsDeclarer) {
        outputFieldsDeclarer.declare(new Fields("word"));
    }
}
