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

public class CommitFeedListenerSpout extends BaseRichSpout {

    private SpoutOutputCollector collector;
    private List<String> commits;

    @Override
    public void declareOutputFields(OutputFieldsDeclarer declarer) {
        declarer.declare(new Fields("commit"));
    }

    @Override
    public void open(Map<String, Object> conf, TopologyContext context, SpoutOutputCollector collector) {
        this.collector = collector;
        commits = IOUtils.readLines(
                getClass().getClassLoader().getResourceAsStream("changelog.txt"),
                Charset.defaultCharset().name()
        );
    }

    @Override
    public void nextTuple() {
        for (String commit : commits) {
            collector.emit(new Values(commit));
        }
    }


    @Override
    public void ack(Object id) {
    }

    @Override
    public void fail(Object id) {
    }
}
