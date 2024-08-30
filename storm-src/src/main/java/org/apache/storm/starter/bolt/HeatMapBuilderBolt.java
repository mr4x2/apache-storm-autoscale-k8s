package org.apache.storm.starter.bolt;

import com.google.code.geocoder.model.LatLng;
import org.apache.storm.Config;
import org.apache.storm.Constants;
import org.apache.storm.task.TopologyContext;
import org.apache.storm.topology.BasicOutputCollector;
import org.apache.storm.topology.OutputFieldsDeclarer;
import org.apache.storm.topology.base.BaseBasicBolt;
import org.apache.storm.tuple.Tuple;
import org.apache.storm.tuple.Values;

import java.util.*;

public class HeatMapBuilderBolt extends BaseBasicBolt {
    private Map<Long, List<LatLng>> heatmaps;

    @Override
    public void prepare(Map<String, Object> topoConf, TopologyContext context) {
        heatmaps = new HashMap<Long, List<LatLng>>();
    }

    @Override
    public Map<String, Object> getComponentConfiguration() {
        Config conf = new Config();
        conf.put(Config.TOPOLOGY_TICK_TUPLE_FREQ_SECS, 60);
        return conf;
    }

    @Override
    public void execute(Tuple input, BasicOutputCollector collector) {
        if (isTickTuple(input)) {
            emitHeatmap(collector);
        }
        else {
            Long time = input.getLongByField("time");
            LatLng geocode = (LatLng) input.getValueByField("geocode");

            Long timeInterval = selectTimeInterval(time);
            List<LatLng> checkins = getCheckinsForInterval(timeInterval);
            checkins.add(geocode);
        }

    }

    @Override
    public void declareOutputFields(OutputFieldsDeclarer declarer) {

    }

    private Long selectTimeInterval(Long time) {
        return time / (15 * 1000);
    }

    private List<LatLng> getCheckinsForInterval(Long timeInterval) {
        List<LatLng> hotzones = heatmaps.get(timeInterval);
        if (hotzones == null) {
            hotzones = new ArrayList<LatLng>();
            heatmaps.put(timeInterval, hotzones);
        }
        return hotzones;
    }

    private boolean isTickTuple(Tuple tuple) {
        String sourceComponent = tuple.getSourceComponent();
        String sourceStreamId = tuple.getSourceStreamId();
        return sourceComponent.equals(Constants.SYSTEM_COMPONENT_ID) && sourceStreamId.equals(Constants.SYSTEM_TICK_STREAM_ID);
    }

    private void emitHeatmap(BasicOutputCollector outputCollector){
        Long now = System.currentTimeMillis();
        Long emitUpToTimeInterval = selectTimeInterval(now);
        Set<Long> timeIntervalAvailable = heatmaps.keySet();
        for (Long timeInterval:timeIntervalAvailable){
            if (timeInterval<=emitUpToTimeInterval){
                List<LatLng> hotzones = heatmaps.remove(timeInterval);
                outputCollector.emit(new Values(timeInterval, hotzones));
            }
        }
    }
}
