default: dist_keycloak/keycloak-theme-for-kc-22-and-above.jar

dist_keycloak/keycloak-theme-for-kc-22-and-above.jar: node_modules public/ src/ src/login/
	npm run build-keycloak-theme

node_modules:
	yarn
