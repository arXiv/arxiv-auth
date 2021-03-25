# Setup of for accounts in a GCP project
set -u

source config.sh

#################### Setup accounts VM group  ####################
gcloud compute instance-groups managed describe --project=$PROJECT accounts-mig
LACKS_MIG=$?
if [ ! $LACKS_MIG ]
then
    echo "Skipping create instance group since one exists"
    exit
fi
#set -vueo pipefail
set -uv
# # Need to open the firewall to perform health check on instances
gcloud compute firewall-rules create allow-accounts-health-check \
       --project=$PROJECT \
       --allow tcp:$PORT \
       --source-ranges 130.211.0.0/22,35.191.0.0/16 \
       --network default

TEMPLATE="accounts-template-$(date +%Y%m%d-%H%M%S)"

# make template
#https://cloud.google.com/compute/docs/instance-templates/create-instance-templates#with-container
gcloud compute instance-templates create-with-container $TEMPLATE \
       --project=$PROJECT \
       --machine-type e2-medium \
       --tags=allow-accounts-health-check \
       --container-image $IMAGE_URL \
       --container-env-file=env_values.txt

# Make health check for instance group
# Host is mandatory since Flask will mysteriously 404 if it deosn't match SERVER_NAME
gcloud compute health-checks create http accounts-health-check \
       --project=$PROJECT \
       --check-interval=45s \
       --timeout=15s \
       --unhealthy-threshold=3 \
       --host=phoenix.arxiv.org \
       --request-path=/login \
       --port=$PORT

# make instance group
gcloud compute instance-groups managed create accounts-mig \
       --project=$PROJECT \
       --base-instance-name accounts \
       --size 1 \
       --zone=$ZONE \
       --template $TEMPLATE \
       --health-check accounts-health-check \
       --initial-delay=120s

# Set named port for the load balancer to pick up. By default, the load
# balancer is looking for http.
gcloud compute instance-groups managed set-named-ports accounts-mig \
       --project=$PROJECT \
       --named-ports accounts-http:$PORT  \
       --zone=$ZONE
