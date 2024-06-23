import threading
import time

import docker

from flask import Flask
from prometheus_client import make_wsgi_app, Enum, Gauge
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from waitress import serve

app = Flask(__name__)
cli = docker.DockerClient(base_url="unix:///var/run/docker.sock")

# Add prometheus wsgi middleware to route /metrics requests
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': make_wsgi_app()
})

# Define metrics.
CONTAINER_RESTART_COUNT = Gauge('container_restart_count', 'Number of times a container has been restarted', ['name', 'compose_project', 'compose_service'])
CONTAINER_OOM_KILLED = Gauge('container_oom_killed', 'Is the container OOMKilled', ['name', 'compose_project', 'compose_service'])
CONTAINER_STATUS = Enum('container_status', 'Container Status', ['name', 'compose_project', 'compose_service'], states=['restarting', 'running', 'paused', 'exited'])

def make_metrics():
    def update_metrics():
        containers = cli.containers.list()

        for container in containers:
            oomkilled = 1 if container.attrs['State']['OOMKilled'] else 0

            CONTAINER_RESTART_COUNT.labels(
                name=container.name,
                compose_project=container.labels.get('com.docker.compose.project', ''),
                compose_service=container.labels.get('com.docker.compose.service', ''),
            ).set(container.attrs['RestartCount'])

            CONTAINER_OOM_KILLED.labels(
                name=container.name,
                compose_project=container.labels.get('com.docker.compose.project', ''),
                compose_service=container.labels.get('com.docker.compose.service', ''),
            ).set(oomkilled)

            CONTAINER_STATUS.labels(
                name=container.name,
                compose_project=container.labels.get('com.docker.compose.project', ''),
                compose_service=container.labels.get('com.docker.compose.service', ''),
            ).state(container.status)

        time.sleep(5)
        update_metrics()

    update_metrics()

if __name__ == '__main__':
    t1 = threading.Thread(target=make_metrics)
    t1.start()
    serve(app, host="0.0.0.0", port=9090)
