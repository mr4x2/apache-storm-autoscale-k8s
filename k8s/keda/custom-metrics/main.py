from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_api_client import PrometheusConnect

app = FastAPI()

# Define data model for requests
class MetricSpec(BaseModel):
    metricName: str
    targetValue: int

# This is the endpoint KEDA calls to check if scaling is needed
@app.get("/isActive")
async def is_active():
    # Logic to determine if scaling is needed
    # e.g., checking a custom data source or calculation
    should_scale = custom_check()  # Replace with your logic
    return {"isActive": should_scale}

# This endpoint returns the metric specification to KEDA
@app.get("/getMetricSpec")
async def get_metric_spec():
    # Define the metric your scaler will monitor
    return [{"metricName": "custom_metric", "targetValue": 3}]

# Endpoint for KEDA to fetch the actual metric value
@app.get("/getMetrics")
async def get_metrics():
    # Custom logic to pull metric data
    current_value = fetch_custom_metric()  # Replace with your logic
    return {"metricValues": [{"metricName": "custom_metric", "metricValue": current_value}]}

def custom_check():
    # Replace with custom logic
    return True if fetch_custom_metric() > 3 else False

prom = PrometheusConnect(url="https://prometheus.tuda.freeddns.org")

def fetch_custom_metric():
    try:
        # Execute PromQL query
        query = 'worker_cluster_used{ClusterHost="ui:8081"}'
        result = prom.custom_query(query=query)
        # Extract the value (assuming it's a scalar or single result)
        if result and len(result) > 0:
            print(result[0]['value'][1])
            return float(result[0]['value'][1])  # [0]['value'][1] contains the metric value
        else:
            return 0.0  # Default value if no result
    except Exception as e:
        print(f"Error fetching metric: {e}")
        return 0.0
