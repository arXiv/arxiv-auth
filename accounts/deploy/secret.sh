# Setup of for accounts in a GCP project
# Not currently used.

set -e

source config.sh


#################### Create and store a JWT_SECRET ####################
gcloud services enable secretmanager.googleapis.com
openssl rand -base64 32 | \
    gcloud secrets create jwt-secret \
           --project=$PROJECT \
           --replication-policy="automatic" \
           --data-file=-
