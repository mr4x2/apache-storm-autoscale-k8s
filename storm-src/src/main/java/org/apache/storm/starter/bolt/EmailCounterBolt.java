package org.apache.storm.starter.bolt;

import org.apache.storm.task.TopologyContext;
import org.apache.storm.topology.BasicOutputCollector;
import org.apache.storm.topology.OutputFieldsDeclarer;
import org.apache.storm.topology.base.BaseBasicBolt;
import org.apache.storm.tuple.Tuple;

import java.util.HashMap;
import java.util.Map;

public class EmailCounterBolt extends BaseBasicBolt {
    private Map<String, Integer> counts;

    @Override
    public void execute(Tuple input, BasicOutputCollector collector) {
        String email = input.getStringByField("email");
        counts.put(email, countFor(email) + 1);
        printCounts();
    }

    @Override
    public void prepare(Map<String, Object> topoConf, TopologyContext context) {
        counts = new HashMap<String, Integer>();
    }

    @Override
    public void declareOutputFields(OutputFieldsDeclarer declarer) {
//        not need to define anything in here
    }

    private int countFor(String email) {
        Integer count = counts.get(email);
        return count == null ? 0 : count;
    }

    private void printCounts() {
        for (String email : counts.keySet()) {
            System.out.println(
                    String.format("%s has count %s", email, counts.get(email))
            );
        }
    }

}
