package org.apache.storm.starter;

import org.apache.storm.generated.StormTopology;
import org.apache.storm.starter.bolt.GeoCodeLookUpBolt;
import org.apache.storm.starter.bolt.HeatMapBuilderBolt;
import org.apache.storm.starter.spout.CheckinSpout;
import org.apache.storm.topology.TopologyBuilder;

public class HeatMapTopologyBuilder {
    public static StormTopology build() {
        TopologyBuilder builder = new TopologyBuilder();

        builder.setSpout("CheckinSpout", new CheckinSpout());
        builder.setBolt("GeoCode", new GeoCodeLookUpBolt()).shuffleGrouping("CheckinSpout");
        builder.setBolt("HeatMapBuilder", new HeatMapBuilderBolt()).globalGrouping("GeoCode");
        return builder.createTopology();
    }
}

