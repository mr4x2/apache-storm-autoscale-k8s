package org.apache.storm.starter.rulebase.v1;

import org.apache.storm.starter.metric.BoltMetrics;
import org.apache.storm.starter.metric.BoltMetricsUpdater;

import java.util.Comparator;

public class BoltMetricsComparator implements Comparator<ComponentNode> {

    @Override
    public int compare(ComponentNode x, ComponentNode y) throws NullPointerException {
        BoltMetrics boltStatsX = ((BoltMetricsUpdater) x.getNode().getComponentUpdater()).getBoltMetrics();
        BoltMetrics boltStatsY = ((BoltMetricsUpdater) y.getNode().getComponentUpdater()).getBoltMetrics();

        //We want descending order so that's why we return -1 if capacityX > capacityY
        if (boltStatsX.getCapacity() > boltStatsY.getCapacity()) return -1;

        if (boltStatsX.getCapacity() < boltStatsY.getCapacity()) return 1;

        return 0;
    }

}
