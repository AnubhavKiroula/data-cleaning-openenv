# Monitoring

This project includes a basic uptime check and Prometheus metrics exposure.

## Healthcheck (GitHub Action)

- A scheduled GitHub Action (.github/workflows/monitoring-ping.yml) pings the Space health endpoint every 15 minutes.
- If the healthcheck fails, the workflow creates a GitHub issue notifying maintainers.

## Prometheus metrics

- Backend exposes `/metrics` (Prometheus text format).
- You can configure Prometheus to scrape `https://01ammu-data-cleaning-openenv.hf.space/metrics`.
- A sample Prometheus scrape config is included in `infra/prometheus.yml`.

## Recommendations

- Configure an alerting/notification channel for critical failures (PagerDuty, Email, Slack).
- Add more detailed application-level metrics (job latency, queue length, errors) via `prometheus_client`.
- Consider adding uptime checks for the frontend after deployment (Vercel URL).
