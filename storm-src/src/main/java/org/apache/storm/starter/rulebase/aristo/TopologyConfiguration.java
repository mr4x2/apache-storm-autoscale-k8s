package org.apache.storm.starter.rulebase.aristo;

import org.apache.storm.starter.metric.BoltMetrics;
import org.apache.storm.starter.metric.SpoutMetrics;

import java.util.HashMap;
import java.util.Map;

public class TopologyConfiguration {

    private Map<String, Integer> components;
    private Integer workers;

    public TopologyConfiguration(Integer workers, Map<String, SpoutMetrics> spoutMap, Map<String, BoltMetrics> boltMap) {
        this.workers = workers;

        components = new HashMap<>();

        for (SpoutMetrics spout : spoutMap.values())
            components.put(spout.getId(), spout.getExecutors());

        for (BoltMetrics bolt : boltMap.values())
            components.put(bolt.getId(), bolt.getExecutors());
    }

    public String output() {
        String output = "workers=" + workers + " ";
        for (String key : components.keySet())
            output += key + "=" + components.get(key) + " ";

        return output;
    }
}
