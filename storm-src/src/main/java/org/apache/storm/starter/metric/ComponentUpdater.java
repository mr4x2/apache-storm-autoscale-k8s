package org.apache.storm.starter.metric;

public class ComponentUpdater {

    private BoltMetricsUpdater boltUpdater;
    private SpoutMetricsUpdater spoutUpdater;
    private int componentType;

    public ComponentUpdater(ComponentMetricsCreator component) throws Exception {
        componentType = component.getComponentType();
        if (componentType == 1) {
            boltUpdater = new BoltMetricsUpdater(component);
            spoutUpdater = null;
        } else if (componentType == 2) {
            spoutUpdater = new SpoutMetricsUpdater(component);
            boltUpdater = null;
        } else
            throw new Exception("Unknown component type " + component.getComponentType());
    }

    public void update() {
        if (componentType == 1)
            boltUpdater.updateMetrics();
        else if (componentType == 2)
            spoutUpdater.updateMetrics();
    }

    public void print() {
        if (componentType == 1)
            boltUpdater.printMetrics();
        else if (componentType == 2)
            spoutUpdater.printMetrics();
    }

    public BoltMetricsUpdater getBoltUpdater() {
        return boltUpdater;
    }

    public SpoutMetricsUpdater getSpoutUpdater() {
        return spoutUpdater;
    }
}
