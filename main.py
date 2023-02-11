import uuid
from datetime import timedelta, datetime
from os import environ

import prometheus_client
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from prometheus_client import Gauge
from requests import get

app = FastAPI()

# Disable unwanted metrics
environ.setdefault("PROMETHEUS_DISABLE_CREATED_SERIES", "True")

DEFAULT_SINCE_SECONDS = 20 * 60


@app.get("/")
def read_root():
    return {"Presearch": "Exporter"}


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


@app.get("/metrics")
def metrics(token: str, since_seconds: int = DEFAULT_SINCE_SECONDS):
    # Registry per request
    registry = prometheus_client.CollectorRegistry(auto_describe=True)
    pre_info = Gauge('pre_info', 'Description of gauge', labelnames=LABELS, registry=registry)
    pre_connected = Gauge('pre_connected', 'Description of gauge', labelnames=["node_id"], registry=registry)
    pre_blocked = Gauge('pre_blocked', 'Description of gauge', labelnames=["node_id"], registry=registry)
    pre_connections = Gauge('pre_connections', 'Description of gauge', labelnames=["node_id"], registry=registry)
    pre_disconnections = Gauge('pre_disconnections', 'Description of gauge', labelnames=["node_id"], registry=registry)
    period_stats = [
        Gauge(f'pre_{stat}', 'Description of gauge', labelnames=["node_id"], registry=registry)
        for stat in PERIOD_STATS_NAMES
    ]

    # import json
    # with open("example.json") as f:
    #     data = json.load(f)

    # Fetch stats from API
    url = f"https://nodes.presearch.org/api/nodes/status/{token}"
    start_date = datetime.utcnow() - timedelta(seconds=since_seconds)
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
        pre_info.labels(**labels).set(1)
        pre_connected.labels(node_id).set(1 if node["status"]["connected"] else 0)
        pre_blocked.labels(node_id).set(1 if node["status"]["blocked"] else 0)
        pre_connections.labels(node_id).set(node["period"]["connections"]["num_connections"] or 0)
        pre_disconnections.labels(node_id).set(node["period"]["disconnections"]["num_disconnections"] or 0)
        for stat_name, stat_metric in zip(PERIOD_STATS_NAMES, period_stats):
            stat_metric.labels(node_id).set(node["period"][stat_name] or 0)

    return PlainTextResponse(prometheus_client.generate_latest(registry))
