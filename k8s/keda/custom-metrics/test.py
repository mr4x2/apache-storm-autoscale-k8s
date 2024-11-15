from prometheus_api_client import PrometheusConnect
prom = PrometheusConnect(url="https://prometheus.tuda.freeddns.org")
def fetch_custom_metric():
    try:
        # Execute PromQL query
        query = 'worker_cluster_used{ClusterHost="ui:8081"}'
        result = prom.custom_query(query=query)
        # Extract the value (assuming it's a scalar or single result)
        if result and len(result) > 0:
            print(result[0]["value"][1])
            return float(result[0]['value'][1])  # [0]['value'][1] contains the metric value
            
        else:
            return 0.0  # Default value if no result
    except Exception as e:
        print(f"Error fetching metric: {e}")
        return 0.0

fetch_custom_metric()