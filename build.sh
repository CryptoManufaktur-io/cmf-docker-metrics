poetry run pyinstaller \
--onefile \
--collect-data cmf_docker_metrics ./cmf_docker_metrics/main.py \
--name cmf-docker-metrics \
--distpath build/cmf-docker-metrics
