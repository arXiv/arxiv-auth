app_tag := arxiv-oauth2-client
app_name := arxiv-oauth2-client
app_port := 20241
dockerport := 8080

ROOT_DIR := $(shell pwd)
AAA_CPUS := $(shell echo $${AAA_CPUS:-2})
AAA_WORKERS := $(shell echo $${AAA_WORKERS:-2})
AAA_DOCKER_PLATFORM := $(shell echo $${AAA_DOCKER_PLATFORM:-linux/amd64})
AAA_CALLBACK_URI := $(shell echo $${AAA_CALLBACK_URI:-https://dev3.arxiv.org/callback})
KEYCLOAK_SERVER_URL := ${shell cat ${HOME}/.arxiv/keycloak-url-dev}
CLASSIC_DB_URI := $(shell cat ${HOME}/.arxiv/arxiv-db-dev)
KEYCLOAK_CLIENT_SECRET := $(shell cat ${HOME}/.arxiv/keycloak-secret-dev)

APP_DOCKER_RUN := docker run --cpus ${AAA_CPUS} --rm -p ${app_port}:${dockerport} \
-e PORT=${dockerport} -e WORKERS=${AAA_WORKERS} \
-e KEYCLOAK_SERVER_URL=${KEYCLOAK_SERVER_URL} \
-e OAUTH2_CALLBACK_URL=${AAA_CALLBACK_URI} \
-e KEYCLOAK_CLIENT_SECRET=${KEYCLOAK_CLIENT_SECRET} \
-e CLASSIC_DB_URI=${CLASSIC_DB_URI} \
--name ${app_name} --security-opt="no-new-privileges=true" 

.PHONY: HELLO docker run stop

default: HELLO venv/lib/python3.12/site-packages/fastapi

HELLO:
	@echo To see the README of this Makefile, type "make help"
	@echo Local HTTP port is ${app_port}
	@echo Docker command params is:
	@echo ${APP_DOCKER_RUN}

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
