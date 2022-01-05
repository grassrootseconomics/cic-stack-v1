#!/usr/bin/env sh

# dependencies:
#   - docker-compose >= v1.25.0
#   - sbot >= v1.0.0.

set -e

export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

PREDICTED_TAG=$(sbot predict version -m auto)

docker-compose -f docker-compose.build.yml build --progress plain

export TAG=v$PREDICTED_TAG

docker-compose -f docker-compose.build.yml build --progress plain
docker-compose -f docker-compose.build.yml push

export TAG=latest

docker-compose -f docker-compose.build.yml push
