# Presearch Prometheus Node Exporter

FastAPI server that exposes `/metrics` endpoint to be scraped by Prometheus.

It collects connection, system, and rewards metrics. Everything that is available
in [Presearch API](https://docs.presearch.io/nodes/api).

## Tech

- https://fastapi.tiangolo.com
- https://github.com/prometheus/client_python
- https://prometheus.io
- https://grafana.com

## Prometheus

Example scraping job

```yaml
- job_name: presearch-exporter-1
  scrape_interval: 1m
  scrape_timeout: 45s
  params:
    token: [ "API_TOKEN" ]
  static_configs:
    - targets: [ 'presearch-exporter-deployment.io:8000' ]
      labels: { pre_client: 'nourspace' }
```

## Credits

This codebase is inspired by

- [How to monitor your PRESEARCH nodes with prometheus and grafana ?](https://libremaster.com/presearch-node-grafana/)
  Amazing guide by [Christophe T.](https://libremaster.com/contact/) on how to implement Prometheus/Grafana monitoring
  for Presearch.
- [A prometheus exporter for presearch.io nodes written in go](https://github.com/Zibby/presearch-node-exporter)
  Similar service by [Zibby](https://github.com/Zibby)

## Todo

- [ ] Cleanup and add more docs on complete installation
- [ ] Improve Docker
- [ ] Add more dashboards/panels
