FROM python:3.11-bookworm as builder

RUN python --version

RUN curl -sSL https://install.python-poetry.org | python -

ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

COPY . .

RUN poetry install

RUN ./build.sh

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y ca-certificates bash tzdata hwloc libhwloc-dev wget curl

COPY --from=builder /app/build/cmf-docker-metrics/cmf-docker-metrics /usr/local/bin/

RUN mkdir /var/lib/cmf-docker-metrics && chmod 0777 /var/lib/cmf-docker-metrics

ENTRYPOINT [ "/usr/local/bin/cmf-docker-metrics" ]
