package org.apache.storm.starter.metric;

public class SpoutMetrics {

    private String id;
    private int executors;
    private int tasks;
    private int uptime;
    private long acked;
    private long failed;
    private long emitted;
    private long transfered;
    private double completeLatency;
    private double ackedRate;
    private double emitRate;
    private double transferRate;

    public SpoutMetrics(String id) {
        this.id = id;
        executors = 0;
        tasks = 0;
        uptime = 0;
        acked = 0;
        failed = 0;
        emitted = 0;
        transfered = 0;
        completeLatency = 0;
        ackedRate = 0;
        emitRate = 0;
        transferRate = 0;
    }

    public SpoutMetrics(SpoutMetrics sm) {
        id = sm.getId();
        executors = sm.getExecutors();
        tasks = sm.getTasks();
        uptime = sm.getUptime();
        acked = sm.getAcked();
        failed = sm.getFailed();
        emitted = sm.getEmitted();
        transfered = sm.getTransfered();
        completeLatency = sm.getCompleteLatency();
        ackedRate = sm.getAckedRate();
        emitRate = sm.getEmitRate();
        transferRate = sm.getTransferRate();
    }

    public SpoutMetrics(String id, int executors, int tasks, int uptime, long acked, long failed, long emitted, long transfered, double completeLatency, double ackedRate, double emitRate, double transferRate) {
        this.id = id;
        this.executors = executors;
        this.tasks = tasks;
        this.uptime = uptime;
        this.acked = acked;
        this.failed = failed;
        this.emitted = emitted;
        this.transfered = transfered;
        this.completeLatency = completeLatency;
        this.ackedRate = ackedRate;
        this.emitRate = emitRate;
        this.transferRate = transferRate;
    }

    public String getId() {
        return id;
    }

    //public void setId(String id) { this.id = id; }

    public int getExecutors() {
        return executors;
    }

    public void setExecutors(int executors) {
        this.executors = executors;
    }

    public int getTasks() {
        return tasks;
    }

    public void setTasks(int tasks) {
        this.tasks = tasks;
    }

    public int getUptime() {
        return uptime;
    }

    public void setUptime(int uptime) {
        this.uptime = uptime;
    }

    public long getAcked() {
        return acked;
    }

    public void setAcked(long acked) {
        this.acked = acked;
    }

    public long getEmitted() {
        return emitted;
    }

    public void setEmitted(long emitted) {
        this.emitted = emitted;
    }

    public long getFailed() {
        return failed;
    }

    public void setFailed(long failed) {
        this.failed = failed;
    }

    public long getTransfered() {
        return transfered;
    }

    public void setTransfered(long transfered) {
        this.transfered = transfered;
    }

    public double getCompleteLatency() {
        return completeLatency;
    }

    public void setCompleteLatency(double completeLatency) {
        this.completeLatency = completeLatency;
    }

    public double getAckedRate() {
        return ackedRate;
    }

    public void setAckedRate(double ackedRate) {
        this.ackedRate = ackedRate;
    }

    public double getEmitRate() {
        return emitRate;
    }

    public void setEmitRate(double emitRate) {
        this.emitRate = emitRate;
    }

    public double getTransferRate() {
        return transferRate;
    }

    public void setTransferRate(double transferRate) {
        this.transferRate = transferRate;
    }

    public void PrintSpoutMetrics() {
        System.out.println("-------------------------");
        System.out.println(id);
        System.out.println("uptime :" + uptime);
        System.out.println("executors: " + executors + " / tasks: " + tasks + "\n");
        System.out.println("emitted: " + emitted + " / transfered: " + transfered);
        System.out.println("acked: " + acked + " / failed: " + failed);
        System.out.println("latency: " + completeLatency);
        System.out.println("acked/sec :" + ackedRate);
        System.out.println("emitted/sec :" + emitRate);
        System.out.println("transfered/sec :" + transferRate);
        System.out.println("-------------------------");
    }

}
