# syntax = docker/dockerfile:1.2
FROM python:3.8.6-slim-buster as compile-image

WORKDIR /root

RUN apt-get update
RUN apt-get install -y --no-install-recommends git gcc g++ libpq-dev gawk jq telnet wget openssl iputils-ping gnupg socat bash procps make python2 cargo

RUN mkdir -vp /usr/local/etc/cic

COPY data-seeding/requirements.txt . 

COPY data-seeding/ . 

ARG EXTRA_INDEX_URL="https://pip.grassrootseconomics.net:8433"
RUN pip install --extra-index-url $EXTRA_INDEX_URL -r requirements.txt 


ENTRYPOINT [ ]
