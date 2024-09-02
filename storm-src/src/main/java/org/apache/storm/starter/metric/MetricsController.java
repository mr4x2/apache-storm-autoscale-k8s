package org.apache.storm.starter.metric;

public class MetricsController {

    public static void main(String[] args) throws Exception {

        if (args.length != 2) {
            System.out.println("Usage: Topology name, Component name");
        }

        String topologyName = args[0];
        String componentName = args[1];

        ComponentMetricsCreator component = new ComponentMetricsCreator(topologyName, componentName);


        for (int i = 0; i < 1000; i++) {
            component.getComponentUpdater().updateMetrics();
            component.getComponentUpdater().printMetrics();
            Thread.sleep(10 * 1000);
        }


    }

    public void startMetrics(String topologyName, String componentName) throws Exception {

        ComponentMetricsCreator component = new ComponentMetricsCreator(topologyName, componentName);

        for (int i = 0; i < 1000; i++) {
            component.getComponentUpdater().updateMetrics();
            component.getComponentUpdater().printMetrics();
            Thread.sleep(10 * 1000);
        }
    }

}
