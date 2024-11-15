import os
import time
from dotenv import load_dotenv
from fastapi import FastAPI
from prometheus_api_client import PrometheusConnect
from pydantic import BaseModel

app = FastAPI()

load_dotenv()
nimbus_host = os.getenv('NIMBUS_HOST')
prometheus_host = os.getenv("PROMETHEUS_HOST")

prometheus_client = PrometheusConnect(url=prometheus_host, disable_ssl=True)

# Cache to store fetched metrics
metric_cache = {
    "timestamp": 0,
    "data": {}
}
CACHE_TTL = 30


def fetch_metrics():
    """Fetch all required metrics from Prometheus and store them in cache."""
    global metric_cache
    current_time = time.time()

    # If cache is still valid, return cached data
    if current_time - metric_cache["timestamp"] < CACHE_TTL:
        return metric_cache["data"]

    # Otherwise, fetch fresh data
    try:
        worker_used_query = f'worker_cluster_used{{ClusterHost="{nimbus_host}"}}'
        worker_total_query = f'worker_cluster_total{{ClusterHost="{nimbus_host}"}}'
        bolt_capacity_query = 'avg(avg_over_time(bolts_capacity{BoltId=~"^split-.*"}[10m]))'
        spout_latency_query = 'avg_over_time(spouts_complete_latency{SpoutId="spout-data-iot-data"}[10m])'

        worker_used = prometheus_client.custom_query(query=worker_used_query)
        worker_total = prometheus_client.custom_query(query=worker_total_query)
        bolt_capacity = prometheus_client.custom_query(query=bolt_capacity_query)
        spout_latency = prometheus_client.custom_query(query=spout_latency_query)

        # Calculate worker utilization ratio
        worker_utilization = (
            float(worker_used[0]["value"][1]) / float(worker_total[0]["value"][1])
            if worker_used and worker_total else 0.0
        )

        # Calculate average capacity
        bolt_capacity_avg = (
            float(bolt_capacity[0]["value"][1])
            if bolt_capacity and len(bolt_capacity) > 0 else 0.0
        )

        # Calculate spout latency
        spout_latency_avg = (
            float(spout_latency[0]["value"][1])
            if spout_latency and len(spout_latency) > 0 else 0.0
        )

        metric_cache = {
            "timestamp": current_time,
            "data": {
                "workerUsed": worker_utilization,
                "botlCapacity": bolt_capacity_avg,
                "spoutLatency": spout_latency_avg
            }
        }

        return metric_cache["data"]

    except Exception as e:
        print(f"Error fetching data from Prometheus: {e}")
        return {"workerUsed": 0.0, "botlCapacity": 0.0, "spoutLatency": 0.0}


def custom_calculate():
    weight_total = 0

    keda_threshold = {
        "workerUsed": 0.7,
        "botlCapacity": 0.5,
        "spoutLatency": 100,  # 50 milliseconds
    }

    weight_condition = {
        "workerUsed": 0.6,
        "botlCapacity": 0.2,
        "spoutLatency": 0.2,
    }
    for item, value in fetch_metrics().items():
        weight_total += weight_condition[item] * value / keda_threshold[item]
        print(f"metric{item}: ratio is {weight_condition[item] * value / keda_threshold[item]}")
    return weight_total


# Define data model for requests
class MetricSpec(BaseModel):
    metricName: str
    targetValue: int


@app.get("/isActive")
async def is_active():
    should_scale = custom_check()
    return {"isActive": should_scale}


@app.get("/getMetricSpec")
async def get_metric_spec():
    # Define the metric your scaler will monitor
    return [{"metricName": "custom_metric", "targetValue": 0.7}]


# Endpoint for KEDA to fetch the actual metric value
@app.get("/getMetrics")
async def get_metrics():
    current_value = custom_calculate()
    return {
        "metricValues": [
            {"metricName": "custom_metric", "metricValue": current_value},
            {"metricName": "specificMetrics", "metricValue": fetch_metrics()}
        ]
    }


def custom_check():
    return True if custom_calculate() > 0.7 else False
