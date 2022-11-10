ARG DOCKER_REGISTRY="ghcr.io/grassrootseconomics"

FROM $DOCKER_REGISTRY/base-image:v1

WORKDIR /root

RUN touch /etc/apt/sources.list.d/ethereum.list
RUN echo 'deb http://ppa.launchpad.net/ethereum/ethereum/ubuntu bionic main' > /etc/apt/sources.list.d/ethereum.list
RUN echo 'deb-src http://ppa.launchpad.net/ethereum/ethereum/ubuntu bionic main' >> /etc/apt/sources.list.d/ethereum.list
RUN cat /etc/apt/sources.list.d/ethereum.list
RUN apt-key adv --keyserver keyserver.ubuntu.com  --recv-keys 2A518C819BE37D2C2031944D1C52189C923F6CA9

RUN mkdir -vp /usr/local/etc/cic
# create secrets directory
RUN mkdir -vp pgp/keys

COPY requirements.txt .

#RUN apt-get install libffi-dev

ARG pip_index_url=https://pypi.org/simple
ARG EXTRA_PIP_INDEX_URL="https://pip.grassrootseconomics.net"
ARG EXTRA_PIP_ARGS=""
ARG PIP_INDEX_URL="https://pypi.org/simple"
ARG pip_trusted_host=pypi.org
RUN pip install --index-url $PIP_INDEX_URL \
    --pre \
    --extra-index-url $EXTRA_PIP_INDEX_URL $EXTRA_PIP_ARGS \
    -r requirements.txt

RUN pip freeze

COPY . .
RUN chmod +x *.sh
