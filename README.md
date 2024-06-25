# cmf-docker-metrics

Custom metrics exporter for docker compose.

Expects the `/var/run/docker.sock` socket to exist in order to work.

Endpoint: `/metrics`

Port: `9090`

## Exported metrics:

- container_restart_count
- container_status
- container_oom_killed
- service_running_replicas
- service_desired_replicas
