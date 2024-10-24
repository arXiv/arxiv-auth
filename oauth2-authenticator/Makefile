include .env
export $(shell sed 's/=.*//' .env)

app_tag := arxiv-oauth2-client
app_name := arxiv-oauth2-client
app_port := 20241
dockerport := 8080

ROOT_DIR := $(shell pwd)
AAA_CPUS := $(shell echo $${AAA_CPUS:-2})
AAA_WORKERS := $(shell echo $${AAA_WORKERS:-2})
AAA_DOCKER_PLATFORM := $(shell echo $${AAA_DOCKER_PLATFORM:-linux/amd64})
# AAA_CALLBACK_URL := $(shell echo $${AAA_CALLBACK_URL:-https://dev3.arxiv.org/aaa/callback})
KEYCLOAK_SERVER_URL := ${shell cat ${HOME}/.arxiv/keycloak-url-dev}
CLASSIC_DB_URI := $(shell cat ${HOME}/.arxiv/arxiv-db-dev)
KEYCLOAK_CLIENT_SECRET := $(shell cat ${HOME}/.arxiv/keycloak-secret-dev)
JWT_SECRET := $(shell cat ${HOME}/.arxiv/jwt-secret)
CLASSIC_SESSION_HASH := $(shell cat ${HOME}/.arxiv/tapir-classic-session-hash)
#DOMAIN := $(shell cat ${HOME}/.arxiv/domain)

APP_DOCKER_RUN := docker run --cpus ${AAA_CPUS} --rm -p ${app_port}:${dockerport} \
-e PORT=${dockerport} -e WORKERS=${AAA_WORKERS} \
-e KEYCLOAK_SERVER_URL=${KEYCLOAK_SERVER_URL} \
-e OAUTH2_CALLBACK_URL=${AAA_CALLBACK_URL} \
-e KEYCLOAK_CLIENT_SECRET=${KEYCLOAK_CLIENT_SECRET} \
-e CLASSIC_DB_URI=${CLASSIC_DB_URI} \
-e SESSION_DURATION=36000 \
-e CLASSIC_COOKIE_NAME=tapir_session \
-e CLASSIC_SESSION_HASH=${CLASSIC_SESSION_HASH} \
-e JWT_SECRET=${JWT_SECRET} \
--name ${app_name} --security-opt="no-new-privileges=true"

# -e DOMAIN=${DOMAIN} \


.PHONY: HELLO docker run stop

default: HELLO venv/lib/python3.12/site-packages/fastapi

HELLO:
	@echo To see the README of this Makefile, type "make help"
	@echo Local HTTP port is ${app_port}
	@echo Docker command params is:
	@echo ${APP_DOCKER_RUN}

bootstrap: venv/lib/python3.12/site-packages/fastapi

#-#
#-# Command: help
#-#   show this message
help:
	@awk '/^#-#/ { print substr($$0, 5)}' Makefile

#-#
#-# Command: docker
#-#   builds the docker image
docker:
	@echo "PLATFORM: ${PLATFORM}"
	@echo "dockerport: ${app_port}"
	@echo "tag: ${app_tag}"
	docker buildx build -f ./Dockerfile \
		--security-opt seccomp=unconfined  \
		--progress=plain \
		--platform=linux/amd64 -t ${app_tag}:latest .

#-#
#-# Command: run
#-#   runs the appliance container with the terminal attached (for test)
run: stop
	${APP_DOCKER_RUN} -it ${app_tag}:latest

#-#
#-# Command: stop
#-#   stops the appliance container
stop:
	-docker container kill ${app_name}
	-docker container rm ${app_name}

#-#
#-# Command: sh
#-#   runs a bash shell in the container to look inside of it
sh: stop
	${APP_DOCKER_RUN}  -v ${HOME}/Downloads:/home/worker/Downloads -w /home/worker -it ${app_tag}:latest  /bin/bash

#-#
#-# Command: daemon
#-#   runs the appliance container with the terminal attached (for test)
daemon: stop
	${APP_DOCKER_RUN} -d ${app_tag}:latest


/usr/bin/python3.12:
	sudo apt install -y python3.12

/usr/lib/python3.12/ensurepip/__init__.py:
	sudo apt install -y python3.12-venv

.bootstrap:
	sudo apt install -y libmysqlclient-dev build-essential python3.12-dev
	touch .bootstrap

venv/bin/poetry: /usr/bin/python3.12 /usr/lib/python3.12/ensurepip/__init__.py .bootstrap
	python3.12 -m venv venv
	. venv/bin/activate && pip install --upgrade pip && pip install poetry

venv/lib/python3.12/site-packages/fastapi: venv/bin/poetry
	. venv/bin/activate && poetry install

/usr/bin/docker:
	sh ./install-docker.sh

show-env:
	sed -e 's/^/export /g' .env


