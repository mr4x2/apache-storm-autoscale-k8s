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
import java.util.Random;

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
            Random random = new Random();
            collector.emit(new Values(commit), random.nextInt(999999));
        }
    }


    @Override
    public void ack(Object id) {
        System.out.println("Tuple with ID " + id + " acknowledged.");
    }

    @Override
    public void fail(Object id) {
        System.out.println("Tuple with ID " + id + " failed.");
        // You can implement logic here to re-emit the tuple or handle the failure
    }
}
