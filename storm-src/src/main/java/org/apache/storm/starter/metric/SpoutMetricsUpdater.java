package org.apache.storm.starter.metric;

import org.apache.storm.generated.SpoutAggregateStats;
import org.apache.storm.generated.CommonAggregateStats;
import org.apache.storm.generated.ComponentPageInfo;
import org.apache.storm.generated.ExecutorAggregateStats;

public class SpoutMetricsUpdater implements ComponentMetricsUpdaterInterface{

    private SpoutMetrics spoutMetrics;
    private ComponentMetricsCreator component;

    public SpoutMetricsUpdater(ComponentMetricsCreator component) throws Exception{
        if (component.getComponentType() != 2)
            throw  new Exception("Illegal component type " + component.getComponentType());

        this.component = component;
        spoutMetrics = new SpoutMetrics(component.getComponentId());
    }

    public void updateMetrics() {
        try {
            ComponentPageInfo componentPage = component.getClient().getComponentPageInfo(component.getTopologyId(), component.getComponentId(), ":all-time", false);
            spoutMetrics.setExecutors(componentPage.get_num_executors());
            spoutMetrics.setTasks(componentPage.get_num_tasks());

            int uptime = component.getClient().getTopologyInfo(component.getTopologyId()).get_uptime_secs();
            long totalAcked = 0;
            long totalFailed = 0;
            long totalEmitted = 0;
            long totalTransfered = 0;
            double avgCompleteLatency = 0;

            for (ExecutorAggregateStats stats: componentPage.get_exec_stats()) {
                CommonAggregateStats common = stats.get_stats().get_common_stats();
                SpoutAggregateStats specific = stats.get_stats().get_specific_stats().get_spout();

                totalAcked += common.get_acked();
                totalFailed += common.get_failed();
                totalEmitted += common.get_emitted();
                totalTransfered += common.get_transferred();

                avgCompleteLatency += specific.get_complete_latency_ms()*common.get_acked();


            }

            spoutMetrics.setAckedRate((double)(totalAcked - spoutMetrics.getAcked()) / (uptime - spoutMetrics.getUptime()));
            spoutMetrics.setEmitRate((double)(totalEmitted - spoutMetrics.getEmitted()) / (uptime - spoutMetrics.getUptime()));
            spoutMetrics.setTransferRate((double)(totalTransfered - spoutMetrics.getTransfered()) / (uptime - spoutMetrics.getUptime()));

            spoutMetrics.setCompleteLatency(avgCompleteLatency / totalAcked);

            spoutMetrics.setUptime(uptime);
            spoutMetrics.setAcked(totalAcked);
            spoutMetrics.setFailed(totalFailed);
            spoutMetrics.setEmitted(totalEmitted);
            spoutMetrics.setTransfered(totalTransfered);
        }
        catch (Exception e){
            e.printStackTrace();
        }
    }

    public void printMetrics() {
        spoutMetrics.PrintSpoutMetrics();
    }

    public SpoutMetrics getSpoutMetrics() {
        return spoutMetrics;
    }

    public ComponentMetricsCreator getComponent() {
        return component;
    }

}

