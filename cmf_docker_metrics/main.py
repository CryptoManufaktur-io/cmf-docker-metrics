import threading
import time
import logging

import docker

from flask import Flask
from prometheus_client import make_wsgi_app, Enum, Gauge
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from waitress import serve

logging.basicConfig()

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

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

# Swarm.
SERVICE_RUNNING_REPLICAS = Gauge('service_running_replicas', 'Number of replicas running', ['service_name', 'stack', 'swarm_nodes'])
SERVICE_DESIRED_REPLICAS = Gauge('service_desired_replicas', 'Number of replicas that should be running', ['service_name', 'stack', 'swarm_nodes'])

def make_metrics():
    def update_metrics():
        LOGGER.info("Updating docker metrics...")
        # Get containers metrics.
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

        # If this is a docker swarm, let's get replicas states.
        docker_info = cli.info()

        if docker_info['Swarm']['NodeID'] != "":
            LOGGER.info("Updating Swarm metrics...")
            swarm_nodes_count = docker_info['Swarm']['Nodes']
            services = cli.services.list()

            for service in services:
                replicas = 0
                running = 0

                tasks = service.tasks()

                for task in tasks:
                    # print(task)
                    if task['DesiredState'] != 'shutdown':
                        replicas += 1

                    if task['Status']['State'] == 'running':
                        running += 1

                if service.attrs['Spec']['Mode'].get('Replicated'):
                    replicas = service.attrs['Spec']['Mode']['Replicated']['Replicas']

                SERVICE_RUNNING_REPLICAS.labels(
                    service_name=service.name,
                    stack=service.attrs['Spec']['Labels'].get('com.docker.stack.namespace', ''),
                    swarm_nodes=swarm_nodes_count,
                ).set(running)

                SERVICE_DESIRED_REPLICAS.labels(
                    service_name=service.name,
                    stack=service.attrs['Spec']['Labels'].get('com.docker.stack.namespace', ''),
                    swarm_nodes=swarm_nodes_count,
                ).set(running)

        LOGGER.info("Done.")

        time.sleep(5)
        update_metrics()

    update_metrics()

if __name__ == '__main__':
    t1 = threading.Thread(target=make_metrics)
    t1.start()
    serve(app, host="0.0.0.0", port=9090)
