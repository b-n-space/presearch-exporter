import uuid
from datetime import timedelta, datetime
from os import environ

import prometheus_client
import uvicorn
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from prometheus_client import Gauge
from requests import get

app = FastAPI()

# Disable unwanted metrics
environ.setdefault("PROMETHEUS_DISABLE_CREATED_SERIES", "True")

DEFAULT_SINCE_MINUTES = 15
ALLOWED_STATS_MINUTES = [0, 15, 22, 30, 45]


@app.get("/")
def read_root():
    return {"Presearch": "Exporter"}


NAMESPACE = "pre"
LABELS = ["node_id", "node_description", "node_url", "gateway_pool", "remote_addr", "version"]
PERIOD_STATS_NAMES = [
    "total_uptime_seconds",
    "uptime_percentage",
    "avg_uptime_score",
    "avg_latency_ms",
    "avg_latency_score",
    "total_requests",
    "successful_requests",
    "avg_success_rate",
    "avg_success_rate_score",
    "avg_reliability_score",
    "avg_staked_capacity_percent",
    "avg_utilization_percent",
    "total_pre_earned",
    "rewardable_requests",
]


def create_registry(stats):
    registry = prometheus_client.CollectorRegistry(auto_describe=True)
    node_info = Gauge('node_info', 'Description', labelnames=LABELS, namespace=NAMESPACE, registry=registry)
    connected = Gauge('connected', 'Description', labelnames=["node_id"], namespace=NAMESPACE, registry=registry)
    blocked = Gauge('blocked', 'Description', labelnames=["node_id"], namespace=NAMESPACE, registry=registry)
    main_metrics = [node_info, connected, blocked]
    if stats:
        connections = Gauge(
            'connections', 'Description', labelnames=["node_id"], namespace=NAMESPACE, registry=registry
        )
        disconnections = Gauge(
            'disconnections', 'Description', labelnames=["node_id"], namespace=NAMESPACE, registry=registry
        )
        period_stats = [
            Gauge(stat, 'Description', labelnames=["node_id"], namespace=NAMESPACE, registry=registry)
            for stat in PERIOD_STATS_NAMES
        ]
        stats_metrics = [connections, disconnections, period_stats]
    else:
        stats_metrics = [None, None, []]
    return registry, main_metrics, stats_metrics


@app.get("/metrics")
def metrics(token: str):
    # We only fetch stats at minutes 0 15 30 45
    utcnow = datetime.utcnow()
    stats = utcnow.minute in ALLOWED_STATS_MINUTES

    # Registry and set of metrics per request
    registry, main_metrics, stats_metrics = create_registry(stats=stats)
    node_info, connected, blocked = main_metrics
    connections, disconnections, period_stats = stats_metrics

    # import json
    # with open("example.json") as f:
    #     data = json.load(f)

    # Fetch stats from API
    url = f"https://nodes.presearch.org/api/nodes/status/{token}"
    params = {}
    if stats:
        start_date = utcnow - timedelta(minutes=DEFAULT_SINCE_MINUTES)
        params = {
            "start_date": start_date.strftime("%Y-%m-%d %H:%M"),
            "stats": "true"
        }
    print(f"Requesting {url=}, {params=}")
    res = get(url=url, params=params)
    data = res.json()
    nodes = data.pop("nodes", {})
    print(f"{data}")
    if res.status_code != 200:
        print(f"Error {data}")
        return PlainTextResponse("", status_code=400)

    # Create metrics per node
    for node_pub, node in nodes.items():
        node_id = uuid.uuid5(uuid.NAMESPACE_DNS, node_pub).hex.upper()
        labels = {
            "node_id": node_id,
            "node_description": node["meta"]["description"] or "",
            "node_url": node["meta"]["url"] or "",
            "gateway_pool": node["meta"]["gateway_pool"],
            "remote_addr": node["meta"]["remote_addr"],
            "version": node["meta"]["version"],
        }
        node_info.labels(**labels).set(1)
        connected.labels(node_id).set(1 if node["status"]["connected"] else 0)
        blocked.labels(node_id).set(1 if node["status"]["blocked"] else 0)
        if stats:
            connections.labels(node_id).set(node["period"]["connections"]["num_connections"] or 0)
            disconnections.labels(node_id).set(node["period"]["disconnections"]["num_disconnections"] or 0)
            for stat_name, stat_metric in zip(PERIOD_STATS_NAMES, period_stats):
                stat_metric.labels(node_id).set(node["period"][stat_name] or 0)

    return PlainTextResponse(prometheus_client.generate_latest(registry))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
