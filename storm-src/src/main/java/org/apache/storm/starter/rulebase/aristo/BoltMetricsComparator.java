package org.apache.storm.starter.rulebase.aristo;

import org.apache.storm.starter.metric.BoltMetrics;
import org.apache.storm.starter.metric.BoltMetricsUpdater;

import java.util.Comparator;

public class BoltMetricsComparator implements Comparator<ComponentNode> {

    @Override
    public int compare(ComponentNode x, ComponentNode y) {
        BoltMetrics boltStatsX = ((BoltMetricsUpdater) x.getNode().getComponentUpdater()).getBoltMetrics();
        BoltMetrics boltStatsY = ((BoltMetricsUpdater) y.getNode().getComponentUpdater()).getBoltMetrics();

        if (boltStatsX.getCapacity() > boltStatsY.getCapacity()) return -1;
        if (boltStatsX.getCapacity() < boltStatsY.getCapacity()) return 1;
        return 0;
    }
}
