#!/bin/bash
cd /home/keycloak
#
# spi-<spi-id>-<provider-id>-<property>=<value>
#
# https://jdbc.postgresql.org/documentation/use/
# export DEBUG=true

if [ "$BOOTSTRAP" = "yes" ] ; then
    echo "Bootstrapping"
    /opt/keycloak/bin/kc.sh start-dev
fi

if [ -z $DB_ADDR ] ; then
  echo "DB_ADDR needs to be set."
  exit 1
fi

if [ -z $DB_PASS ] ; then
  echo "DB_PASS needs to be set."
  exit 1
fi

if [ -r /secrets/authdb-certs/db-certs-expand.sh ] ; then
  echo "Expand db certs"
  cd /home/keycloak/certs && sh /secrets/authdb-certs/db-certs-expand.sh
  ls -l *
  cd /home/keycloak
fi

# -------------------------------------------------------------------------------------------
# Backend DB - Postgres
#
DB_VENDOR="${DB_VENDOR:-postgres}"
DB_DATABASE="${DB_DATABASE:-keycloak}"
DB_USER="${DB_USER:-keycloak}"

# Unfortunate that the vendor name != driver name
JDBC_DRIVER="${JDBC_DRIVER:-postgresql}"

# Database connection certificate setting for postgres db
JDBC_CONNECTION="${JDBC_CONNECTION:-?ssl=true&sslmode=require&sslrootcert=/home/keycloak/certs/server-ca.pem&sslcert=/home/keycloak/certs/client-cert.pem&sslkey=/home/keycloak/certs/client-key.key}"

# This shouldn't change as long as the db is postgres
DB_SCHEMA="${DB_SCHEMA:- --db-schema=public}"

# For prod, set the min larger
DB_POOL="${DB_POOL:- --db-pool-min-size=2}"

# -------------------------------------------------------------------------------------------
# proxy
#
# This is letting keycloak know that the instance is running behind a reverse proxy.
# Since the service is behind he load balancer, this should be the correct value for all cases.
# For local testing, you may want to do something different.
PROXY_MODE="${PROXY_MODE:- --proxy-headers=forwarded}"

# Since the docker is running behind the load balancer, the hostname is always inaccurate.
export KC_HOSTNAME_STRICT=false

# -------------------------------------------------------------------------------------------
# Logging
#
LOG_LEVEL="${LOG_LEVEL:-info}"
LOG_OUTPUT_FORMAT="${LOG_OUTPUT_FORMAT:- --log-console-output=json}"

# -------------------------------------------------------------------------------------------
# Event Listener
#

#export GCP_CREDENTIALS
#export GCP_PROJECT_ID
export GCP_EVENT_TOPIC_ID=keycloak-arxiv-events
export GCP_ADMIN_EVENT_TOPIC_ID=keycloak-arxiv-events

# -------------------------------------------------------------------------------------------
# start / start-dev
#
KEYCLOAK_START="${KEYCLOAK_START:-start-dev}"

/opt/keycloak/bin/kc.sh $KEYCLOAK_START \
  --log-level=$LOG_LEVEL \
  --transaction-xa-enabled=true \
  --db=$DB_VENDOR \
  --db-url="jdbc:$JDBC_DRIVER://$DB_ADDR/$DB_DATABASE$JDBC_CONNECTION" \
  --db-username=$DB_USER \
  --db-password=$DB_PASS \
  $DB_SCHEMA $PROXY_MODE $LOG_OUTPUT_FORMAT
