ARG DOCKER_REGISTRY="ghcr.io/grassrootseconomics"

FROM $DOCKER_REGISTRY/base-image:v1

WORKDIR /root

RUN apt-get install libffi-dev -y

COPY requirements.txt . 

ARG EXTRA_PIP_INDEX_URL="https://pip.grassrootseconomics.net"
ARG EXTRA_PIP_ARGS=""
ARG PIP_INDEX_URL="https://pypi.org/simple"
#RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
RUN    pip install --index-url $PIP_INDEX_URL \
    --pre \
    --extra-index-url $EXTRA_PIP_INDEX_URL $EXTRA_PIP_ARGS \
    -r requirements.txt

COPY . .

#RUN chmod +x *.sh
