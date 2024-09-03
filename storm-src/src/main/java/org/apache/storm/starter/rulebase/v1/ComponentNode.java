package org.apache.storm.starter.rulebase.v1;

import org.apache.storm.starter.metric.ComponentMetricsCreator;

import java.util.ArrayList;


public class ComponentNode {

    private ComponentMetricsCreator node;
    private ArrayList<ComponentNode> neighbors;

    public ComponentNode() {
    }

    public ComponentNode(ComponentMetricsCreator component) {
        node = component;
        neighbors = new ArrayList<ComponentNode>();
    }

    public ComponentMetricsCreator getNode() {
        return node;
    }

    public void setNode(ComponentMetricsCreator node) {
        this.node = node;
    }

    public ArrayList<ComponentNode> getNeighbors() {
        return neighbors;
    }

    public void setNeighbors(ArrayList<ComponentNode> neighbors) {
        this.neighbors = neighbors;
    }

    public void addNeighbor(ComponentNode neighbor) {
        neighbors.add(neighbor);
    }
}
