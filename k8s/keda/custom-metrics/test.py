from prometheus_api_client import PrometheusConnect

from dotenv import load_dotenv
import os

load_dotenv()
nimbus_host = os.getenv('NIMBUS_HOST')
prometheus_host = os.getenv("PROMETHEUS_HOST")

prometheus_client = PrometheusConnect(url=prometheus_host, disable_ssl=True)


def fetch_worker_rate():
    try:
        query_worker_used = f'worker_cluster_used{{ClusterHost="{nimbus_host}"}}'
        result_worker_used = prometheus_client.custom_query(query=query_worker_used)

        query_worker_total = f'worker_cluster_total{{ClusterHost="{nimbus_host}"}}'
        result_worker_total = prometheus_client.custom_query(query=query_worker_total)

        if (result_worker_total and len(result_worker_total) > 0) and (
                result_worker_used and len(result_worker_used) > 0):
            ratio_worker = float(result_worker_used[0]["value"][1]) / float(result_worker_total[0]["value"][1])
            return ratio_worker
        else:
            return 0.0
    except Exception as e:
        print(f"Error fetching metric: {e}")
        return 0.0


def fetch_avg_capacity_split_bolts():
    try:
        query_bolt_capacity_avg = 'avg(avg_over_time(bolts_capacity{BoltId=~"^split-.*"}[10m]))'
        result_bolt_capacity_avg = prometheus_client.custom_query(query=query_bolt_capacity_avg)

        if result_bolt_capacity_avg and len(result_bolt_capacity_avg) > 0:
            return float(result_bolt_capacity_avg[0]["value"][1])
        else:
            return 0

    except Exception as e:
        print(f"Error fetching data from Prometheus: {e}")
        return None


def fetch_avg_complete_latency_spout():
    query_spout_complete_latency_avg = 'avg_over_time(spouts_complete_latency{SpoutId="spout-data-iot-data"}[10m])'
    result = prometheus_client.custom_query(query=query_spout_complete_latency_avg)
    try:
        if result and len(result) > 0:
            return float(result[0]["value"][1])
        else:
            return 0
    except Exception as e:
        print(f"Error fetching data from Prometheus: {e}")
        return None
