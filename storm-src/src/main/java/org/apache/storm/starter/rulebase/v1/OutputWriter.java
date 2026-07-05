package org.apache.storm.starter.rulebase.v1;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.List;

public class OutputWriter {

    private File file;

    public OutputWriter(String topologyName) {
        file = new File(topologyName + "_aristo_rb.txt");
    }

    public void write(String s) throws IOException {
        PrintWriter writer = new PrintWriter(new FileWriter(file, true));
        writer.println(s);
        writer.close();
    }

    public void write(List<TopologyConfiguration> configs, List<Double> throughput, List<Double> latency) throws IOException {
        PrintWriter writer = new PrintWriter(new FileWriter(file, true));
        for (int i = 0; i < configs.size() - 1; i++)
            writer.println(configs.get(i).output() + "throughput=" + throughput.get(i) + " latency=" + latency.get(i));
        writer.println(configs.get(configs.size() - 1).output() + "target reached");
        writer.close();
    }

    public void write(TopologyConfiguration config, Double throughput, Double latency, long time) throws IOException {
        PrintWriter writer = new PrintWriter(new FileWriter(file, true));
        writer.println(config.output() + "throughput=" + throughput + " latency=" + latency + " time_spent_sec=" + time / 1000);
        writer.close();
    }
}
