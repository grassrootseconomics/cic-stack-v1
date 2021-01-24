# The solc image messes up the alpine environment, so we have to go all over again
FROM python:3.8.6-slim-buster

LABEL authors="Louis Holbrook <dev@holbrook.no> 0826EDA1702D1E87C6E2875121D2E7BB88C2A746"
LABEL spdx-license-identifier="GPL-3.0-or-later"
LABEL description="Base layer for buiding development images for the cic component suite"

RUN apt-get update && \
	apt-get install -y git gcc g++ libpq-dev && \
	apt-get install -y vim gawk jq telnet openssl iputils-ping curl wget gnupg socat bash procps make python2 postgresql-client


RUN echo installing nodejs tooling

COPY ./dev/nvm.sh /root/

# Install nvm with node and npm
# https://stackoverflow.com/questions/25899912/how-to-install-nvm-in-docker
ENV NVM_DIR /root/.nvm
ENV NODE_VERSION 15.3.0
ENV BANCOR_NODE_VERSION 10.16.0

RUN wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.37.2/install.sh | bash \
	&& . $NVM_DIR/nvm.sh \
	&& nvm install $NODE_VERSION \
	&& nvm alias default $NODE_VERSION \
	&& nvm use $NODE_VERSION \
# So many ridiculously stupid issues with node in docker that take oceans of absolutely wasted time to resolve
# owner of these files is "1001" by default - wtf
	&& chown -R root:root "$NVM_DIR/versions/node/v$NODE_VERSION"

ENV NODE_PATH $NVM_DIR/versions/node//v$NODE_VERSION/lib/node_modules
ENV PATH      $NVM_DIR/versions/node//v$NODE_VERSION/bin:$PATH

