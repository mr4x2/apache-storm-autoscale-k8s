package org.apache.storm.starter.spout;

import org.apache.storm.shade.org.apache.commons.io.IOUtils;
import org.apache.storm.spout.SpoutOutputCollector;
import org.apache.storm.task.TopologyContext;
import org.apache.storm.topology.OutputFieldsDeclarer;
import org.apache.storm.topology.base.BaseRichSpout;
import org.apache.storm.tuple.Fields;
import org.apache.storm.tuple.Values;

import java.nio.charset.Charset;
import java.util.List;
import java.util.Map;

public class CheckinSpout extends BaseRichSpout {
    private SpoutOutputCollector collector;
    private int nextEmitIndex;
    private List<String> checkins;

    @Override
    public void open(Map<String, Object> conf, TopologyContext context, SpoutOutputCollector collector) {
        this.collector = collector;
        this.nextEmitIndex = 0;
        checkins = IOUtils.readLines(getClass().getClassLoader().getResourceAsStream("heatmap.txt"),
                Charset.defaultCharset().name());

    }

    @Override
    public void nextTuple() {
        String checkin = checkins.get(nextEmitIndex);
        String[] parts = checkin.split(",");
        Long time = Long.valueOf(parts[0]);
        String address = parts[1];
        collector.emit(new Values(time, address));
        nextEmitIndex = (nextEmitIndex + 1) % checkins.size();
    }

    @Override
    public void declareOutputFields(OutputFieldsDeclarer declarer) {
        declarer.declare(new Fields("time", "address"));
    }
}
