
tag := gcr.io/arxiv-development/arxiv-auth/legacy-auth-provider

.PHONY: login docker push deploy run sh

docker:
	docker build --progress=plain --platform=linux/amd64 -t ${tag}:latest .

push:
	docker push ${tag}:latest

deploy:
	gcloud run deploy legacy-auth-provider \
	  --project=arxiv-development \
	  --image=${tag}:latest \
	  --port=8080 \
	  --platform=managed \
	  --allow-unauthenticated \
	  --region=us-central1 \
	  --max-instances=1 \
	  --min-instances=1 \
	  --execution-environment=gen2 \
	  --cpu=1 \
	  --memory=1Gi \
	  --timeout=300 \
	  --concurrency=2 \
	  --set-env-vars SQLALCHEMY_RECORD_QUERIES=true \
	  --set-secrets=CLASSIC_DB_URI=browse-sqlalchemy-db-uri:latest,API_SECRET_KEY=jwt_secret:latest \
	  --session-affinity \
	  --set-cloudsql-instances arxiv-development:us-east4:arxiv-db-dev


run:
	docker run --rm -it --name legacy-auth-provider --network=host -e API_SECRET_KEY=secret -e PORT=3034 -e CLASSIC_DB_URI=mysql://readonly:ro99beta@127.0.0.1:6201/arXiv ${tag}:latest

sh:
	docker run --rm -it --name legacy-auth-provider --network=host -e API_SECRET_KEY=secret PORT=3034 -e CLASSIC_DB_URI=mysql://readonly:ro99beta@127.0.0.1:6201/arXiv --entrypoint=/bin/bash ${tag}:latest

login:
	gcloud auth login
	gcloud config set project arxiv-development
	gcloud auth configure-docker
