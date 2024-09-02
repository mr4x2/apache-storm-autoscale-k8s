package org.apache.storm.starter.metric;

import org.apache.storm.generated.ClusterSummary;
import org.apache.storm.generated.ComponentPageInfo;
import org.apache.storm.generated.Nimbus;
import org.apache.storm.generated.TopologySummary;
import org.apache.storm.utils.NimbusClient;
import org.apache.storm.utils.Utils;

import java.util.Map;

public class ComponentMetricsCreator {


    private String topologyId;
    private String componentId;
    private int componentType;
    private Nimbus.Client client;
    ComponentMetricsUpdaterInterface updater;

    public ComponentMetricsCreator(String topology, String component) throws Exception{

        Map clusterConf = Utils.readStormConfig();
        clusterConf.putAll(Utils.readCommandLineOpts());
        client = (Nimbus.Client) NimbusClient.getConfiguredClient(clusterConf).getClient();

        ClusterSummary summary = client.getClusterInfo();

        topologyId = null;
        for (TopologySummary ts: summary.get_topologies()) {
            if (topology.equals(ts.get_name())) {
                topologyId = ts.get_id();
            }
        }
        if (topologyId == null) {
            throw new Exception("Could not find a topology named "+topology);
        }

        try {
            ComponentPageInfo componentPage = client.getComponentPageInfo(topologyId,component,":all-time",false);
            componentId = componentPage.get_component_id();
            componentType = componentPage.get_component_type().getValue();
        }
        catch (Exception e) {
            e.printStackTrace();
            throw e;
        }



        if (componentType == 1)
            updater = new BoltMetricsUpdater(this);
        else if (componentType == 2)
            updater = new SpoutMetricsUpdater(this);
        else
            throw  new Exception("Unknown component type " + componentType);

    }

    public String getTopologyId() {
        return topologyId;
    }

    public String getComponentId() {
        return componentId;
    }

    public int getComponentType() {
        return componentType;
    }

    public Nimbus.Client getClient() {
        return client;
    }

    public ComponentMetricsUpdaterInterface getComponentUpdater() {
        return updater;
    }
}

