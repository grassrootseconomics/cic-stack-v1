ARG DOCKER_REGISTRY="ghcr.io/grassrootseconomics"

FROM $DOCKER_REGISTRY/base-image/python:v1

COPY requirements.txt .

ARG EXTRA_PIP_INDEX_URL=https://pip.grassrootseconomics.net
ARG EXTRA_PIP_ARGS=""
ARG PIP_INDEX_URL=https://pypi.org/simple

RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    pip install --index-url $PIP_INDEX_URL \
    --pre \
    --extra-index-url $EXTRA_PIP_INDEX_URL $EXTRA_PIP_ARGS \
    -r requirements.txt

COPY . .
RUN pip install .  --extra-index-url $EXTRA_PIP_INDEX_URL

COPY ./aux/wait-for-it/wait-for-it.sh ./
COPY cic_cache/db/migrations/ /usr/local/share/cic-cache/alembic/

COPY /docker/start_tracker.sh ./start_tracker.sh
COPY /docker/db.sh ./db.sh
RUN chmod 755 ./*.sh

ENTRYPOINT []
