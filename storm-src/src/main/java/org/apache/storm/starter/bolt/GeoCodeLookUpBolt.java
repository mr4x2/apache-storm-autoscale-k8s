package org.apache.storm.starter.bolt;

import com.google.code.geocoder.Geocoder;
import com.google.code.geocoder.GeocoderRequestBuilder;
import com.google.code.geocoder.model.*;
import org.apache.storm.task.TopologyContext;
import org.apache.storm.topology.BasicOutputCollector;
import org.apache.storm.topology.OutputFieldsDeclarer;
import org.apache.storm.topology.base.BaseBasicBolt;
import org.apache.storm.tuple.Fields;
import org.apache.storm.tuple.Tuple;
import org.apache.storm.tuple.Values;

import java.io.IOException;
import java.util.Map;

public class GeoCodeLookUpBolt extends BaseBasicBolt {
    private Geocoder geocoder;

    @Override
    public void prepare(Map<String, Object> topoConf, TopologyContext context) {
        geocoder = new Geocoder();
    }

    @Override
    public void execute(Tuple input, BasicOutputCollector collector) {
        String address = input.getStringByField("address");
        Long time = input.getLongByField("time");
        GeocoderRequest request = new GeocoderRequestBuilder().setAddress(address).setLanguage("en").getGeocoderRequest();
        GeocodeResponse response = null;
        try {
            response = geocoder.geocode(request);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
        GeocoderStatus status = response.getStatus();
        if (GeocoderStatus.OK.equals(status)) {
            GeocoderResult firstResult = response.getResults().get(0);
            LatLng latLng = firstResult.getGeometry().getLocation();
            collector.emit(new Values(time, latLng));
        }

    }

    @Override
    public void declareOutputFields(OutputFieldsDeclarer declarer) {
        declarer.declare(new Fields("time", "geocode"));
    }
}
