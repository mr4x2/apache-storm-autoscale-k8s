package org.apache.storm.starter.metric;

public class BoltMetrics {

    private String id;
    private int executors;
    private int tasks;
    private int uptime;
    private long acked;
    private long failed;
    private long emitted;
    private long transfered;
    private long executed;
    private double capacity;
    private double maxCapacity;
    private double processLatency;
    private double executeLatency;
    private double ackedRate;
    private double emitRate;
    private double transferRate;
    private double executeRate;

    public BoltMetrics(String id) {
        this.id = id;
        executors = 0;
        tasks = 0;
        uptime = 0;
        acked = 0;
        failed = 0;
        emitted = 0;
        transfered = 0;
        executed = 0;
        capacity = 0;
        maxCapacity = 0;
        processLatency = 0;
        executeLatency = 0;
        ackedRate = 0;
        emitRate = 0;
        transferRate = 0;
        executeRate = 0;
    }

    public BoltMetrics(BoltMetrics bm) {
        id = bm.getId();
        executors = bm.getExecutors();
        tasks = bm.getTasks();
        uptime = bm.getUptime();
        acked = bm.getAcked();
        failed = bm.getFailed();
        emitted = bm.getEmitted();
        transfered = bm.getTransfered();
        executed = bm.getExecuted();
        capacity = bm.getCapacity();
        maxCapacity = bm.getMaxCapacity();
        processLatency = bm.getProcessLatency();
        executeLatency = bm.getExecuteLatency();
        ackedRate = bm.getAckedRate();
        emitRate = bm.getEmitRate();
        transferRate = bm.getTransferRate();
        executeRate = bm.getExecuteRate();

    }

    public BoltMetrics(String id, int executors, int uptime, int tasks, long acked, double executeRate, double emitRate, double transferRate, double ackedRate, double executeLatency, double processLatency, double capacity, double maxCapacity, long executed, long transfered, long emitted, long failed) {
        this.id = id;
        this.executors = executors;
        this.uptime = uptime;
        this.tasks = tasks;
        this.acked = acked;
        this.executeRate = executeRate;
        this.emitRate = emitRate;
        this.transferRate = transferRate;
        this.ackedRate = ackedRate;
        this.executeLatency = executeLatency;
        this.processLatency = processLatency;
        this.capacity = capacity;
        this.maxCapacity = maxCapacity;
        this.executed = executed;
        this.transfered = transfered;
        this.emitted = emitted;
        this.failed = failed;
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

    public long getFailed() {
        return failed;
    }

    public void setFailed(long failed) {
        this.failed = failed;
    }

    public long getEmitted() {
        return emitted;
    }

    public void setEmitted(long emitted) {
        this.emitted = emitted;
    }

    public long getTransfered() {
        return transfered;
    }

    public void setTransfered(long transfered) {
        this.transfered = transfered;
    }

    public long getExecuted() {
        return executed;
    }

    public void setExecuted(long executed) {
        this.executed = executed;
    }

    public double getCapacity() {
        return capacity;
    }

    public void setCapacity(double capacity) {
        this.capacity = capacity;
    }

    public double getMaxCapacity() {
        return maxCapacity;
    }

    public void setMaxCapacity(double maxCapacity) {
        this.maxCapacity = maxCapacity;
    }

    public double getProcessLatency() {
        return processLatency;
    }

    public void setProcessLatency(double processLatency) {
        this.processLatency = processLatency;
    }

    public double getExecuteLatency() {
        return executeLatency;
    }

    public void setExecuteLatency(double executeLatency) {
        this.executeLatency = executeLatency;
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

    public double getExecuteRate() {
        return executeRate;
    }

    public void setExecuteRate(double executeRate) {
        this.executeRate = executeRate;
    }

    public void PrintSpoutMetrics() {
        System.out.println("-------------------------");
        System.out.println(id);
        System.out.println("uptime :" + uptime);
        System.out.println("executors: " + executors + " / tasks: " + tasks + "\n");
        System.out.println("emitted: " + emitted + " / transfered: " + transfered);
        System.out.println("acked: " + acked + " / failed: " + failed);
        System.out.println("executed: " + executed + " => capacity: " + capacity);
        System.out.println("process latency: " + processLatency + " / execute latency: " + executeLatency);
        System.out.println("acked/sec :" + ackedRate);
        System.out.println("executed/sec :" + executeRate);
        System.out.println("emitted/sec :" + emitRate);
        System.out.println("transfered/sec :" + transferRate);
        System.out.println("-------------------------");
    }
}

