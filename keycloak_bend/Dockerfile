FROM quay.io/keycloak/keycloak:25.0.6

# ARG CERT_DIR

USER root
RUN mkdir -p /home/keycloak/certs

COPY keycloak.conf /opt/keycloak/conf/keycloak.conf
RUN chown keycloak /opt/keycloak/conf/keycloak.conf
#
COPY start-keycloak.sh /home/keycloak/start-keycloak.sh
RUN chmod 755 /home/keycloak/start-keycloak.sh /home/keycloak/certs

COPY ./keycloak_migration/keycloak-user-migration/target/keycloak-rest-provider-5.0.1-SNAPSHOT.jar /opt/keycloak/providers/
#COPY ./pubsub-listener/keycloak-pubsub-listener/target/keycloak-to-pubsub-1.0.0.jar /opt/keycloak/providers/
COPY ./pubsub-listener/keycloak-pubsub-listener/target/keycloak-to-pubsub-jar-with-dependencies.jar /opt/keycloak/providers/
COPY ./arxiv-theme/  /opt/keycloak/themes/arxiv-theme/
COPY ./keycloakify-arxiv/dist_keycloak/keycloak-theme-for-kc-22-and-above.jar /opt/keycloak/providers/keycloakify-arxiv-theme.jar
RUN chown -R keycloak /home/keycloak /opt/keycloak/providers /opt/keycloak/themes/

USER keycloak
WORKDIR /home/keycloak

RUN /opt/keycloak/bin/kc.sh build
ENTRYPOINT ["/home/keycloak/start-keycloak.sh"]
