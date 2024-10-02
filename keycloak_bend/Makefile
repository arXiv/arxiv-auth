
DB_ADDR_PUBLIC := ${shell ./config.sh DB_ADDR_PUBLIC}
DB_ADDR_PRIVATE := ${shell ./config.sh DB_ADDR_PRIVATE}
DB_USER := keycloak
DB_PASS := ${shell ./config.sh DB_PASS}
GCP_CRED := ${shell cat ~/.arxiv/arxiv-development-keycloak-pubsub-sa.b64}
GCP_PROJECT := arxiv-development

KC_ADMIN_PASSWORD=${shell ./config.sh KC_ADMIN_PASSWORD}

tag := gcr.io/arxiv-development/keycloak

.PHONY: run proxy sql docker push deploy

default: .env
	@echo DB_ADDR_PUBLIC: ${DB_ADDR_PUBLIC}  DB_ADDR_PRIVATE:  ${DB_ADDR_PRIVATE}  DB_USER: ${DB_USER} DB_PASS: ${DB_PASS}
	@echo KC_ADMIN_PASSWORD: ${KC_ADMIN_PASSWORD}

.env:
	./config.sh

LOCAL_KEYCLOAK := --name keycloak-local -p 3033:8080 -e LOG_LEVEL="INFO,freemarker:DEBUG" \
 -e GCP_CREDENTIALS="${GCP_CRED}" \
 -e GCP_PROJECT_ID=${GCP_PROJECT} \
 -e BOOTSTRAP=no -e DB_ADDR=${DB_ADDR_PUBLIC} -e DB_USER=keycloak -e DB_PASS=${DB_PASS} -e KEYCLOAK_ADMIN=admin -e KEYCLOAK_ADMIN_PASSWORD=${KC_ADMIN_PASSWORD} -e LOG_OUTPUT_FORMAT="--log-console-output=default"  -v ${PWD}/cert:/secrets/authdb-certs

local:
	docker run -it --rm --name keycloak-local \
	-e KEYCLOAK_ADMIN=admin -e KEYCLOAK_ADMIN_PASSWORD=admin \
	-e KC_HOSTNAME_STRICT=false \
	-p 3033:8080  quay.io/keycloak/keycloak:latest start-dev --db postgres --db-url-host 127.0.0.1 --db-url-port 3030 \
	--db-username ${DB_USER} --db-password ${DB_PASS} 

run:
	docker run --rm -it ${LOCAL_KEYCLOAK} ${tag}:latest 

verbose:
	docker run --rm -it ${LOCAL_KEYCLOAK} -e KEYCLOAK_START='start-dev --verbose' ${tag}:latest 

sh:
	docker run --rm -it ${LOCAL_KEYCLOAK} --entrypoint /bin/bash  ${tag}:latest

proxy:
	/usr/local/bin/cloud-sql-proxy --address 0.0.0.0 --port 3030 arxiv-development:us-central1:authdb > /dev/null 2>&1 &

sql:
	psql "sslmode=verify-ca sslrootcert=${HOME}/.arxiv/dev-authdb/dev-authdb-server-ca.pem sslcert=${HOME}/.arxiv/dev-authdb/dev-authdb-client-cert.pem sslkey=${HOME}/.arxiv/dev-authdb/dev-authdb-client-key.pem hostaddr=$DB_ADDR_PUBLIC port=5432 user=keycloak dbname=keycloak"


docker: keycloak_migration/keycloak-user-migration/target/keycloak-rest-provider-5.0.1-SNAPSHOT.jar pubsub-listener/keycloak-pubsub-listener/target/keycloak-to-pubsub-1.0.0.jar
	docker build --progress plain -t ${tag}:latest .

push:
	docker push ${tag}:latest

init:
	gcloud run deploy keycloak-service --image ${tag}:latest --platform managed --allow-unauthenticated --memory=2Gi --min-instances=1 --max-instances=1 \
	  --region us-central1 --set-env-vars "DB_ADDR=${DB_ADDR_PRIVATE},DB_PASS=PROXY_MODE=--proxy-headers=forwarded,KEYCLOAK_ADMIN=admin,BOOTSTRAP=yes,LOG_OUTPUT_FORMAT=--log-console-output=json,GCP_PROJECT_ID=arxiv-development" \
	  --set-secrets=/secrets/authdb-certs/db-certs-expand.sh=authdb-certs:latest,DB_PASS=authdb-password:latest,KEYCLOAK_ADMIN_PASSWORD=keycloak-admin-password:latest,GCP_CREDENTIALS=keycloak-pubsub-event-sa:latest \

deploy:
	gcloud run deploy keycloak-service \
          --project arxiv-development \
	  --image=${tag}:latest \
	  --platform=managed \
	  --allow-unauthenticated \
	  --region=us-central1 \
	  --max-instances=1 \
	  --min-instances=1 \
	  --cpu=1 \
	  --memory=2Gi \
	  --timeout=300 \
	  --concurrency=80 \
	  --set-env-vars=DB_ADDR=${DB_ADDR_PRIVATE},PROXY_MODE=--proxy-headers=forwarded,KEYCLOAK_ADMIN=admin,BOOTSTRAP=no,LOG_OUTPUT_FORMAT=--log-console-output=json,GCP_PROJECT_ID=arxiv-development \
	  --set-secrets=/secrets/authdb-certs/db-certs-expand.sh=authdb-certs:latest,DB_PASS=authdb-password:latest,KEYCLOAK_ADMIN_PASSWORD=keycloak-admin-password:latest,GCP_CREDENTIALS=keycloak-pubsub-event-sa:latest \
	  --cpu-boost \
	  --session-affinity \
	  --vpc-egress=private-ranges-only

keycloak_migration/keycloak-user-migration/target/keycloak-rest-provider-5.0.1-SNAPSHOT.jar:
	cd keycloak_migration && $(MAKE) keycloak-user-migration/target/keycloak-rest-provider-5.0.1-SNAPSHOT.jar

pubsub-listener/keycloak-pubsub-listener/target/keycloak-to-pubsub-1.0.0.jar:
	cd pubsub-listener && $(MAKE) keycloak-user-migration/target/keycloak-rest-provider-5.0.1-SNAPSHOT.jar
