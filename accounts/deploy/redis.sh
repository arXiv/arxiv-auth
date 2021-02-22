set -e

source config.sh


#################### Start a GCP Managed Redis ####################

#TODO For phoenix-arxiv we could probably do just a super small vm+container
gcloud services enable redis.googleapis.com
gcloud redis instances create auth-jwt-store \
       --tier=basic \
       --redis-version=redis_4_0 \
       --region=$REGION \
       --project=$PROJECT
