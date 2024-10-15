.PHONY: upload-db-certs

default: upload-db-certs

upload-db-certs: dev-authdb-db-certs-expand.sh

dev-authdb-db-certs-expand.sh: dev-authdb-client-cert.pem dev-authdb-client-key.pem dev-authdb-server-ca.pem
	PREFIX=dev-authdb- ./assemble-db-certs.sh

dev-authdb-client-cert.pem:
	./op-get-file.sh wos2wdt56jx2gjmvb4awlxk3ay client-cert.pem > dev-authdb-client-cert.pem

dev-authdb-client-key.pem:
	./op-get-file.sh wos2wdt56jx2gjmvb4awlxk3ay client-key.pem > dev-authdb-client-key.pem

dev-authdb-server-ca.pem:
	./op-get-file.sh wos2wdt56jx2gjmvb4awlxk3ay server-ca.pem > dev-authdb-server-ca.pem
