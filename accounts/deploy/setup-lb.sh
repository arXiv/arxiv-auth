# Setup of for accounts in a GCP project
set -v

source config.sh

#################### Setup load balancer ####################
# This should be done from arxiv-browse/deploy       

#################### accounts backend service ####################

gcloud compute backend-services create accounts-backend \
       --project=$PROJECT \
       --health-checks=accounts-health-check \
       --port-name=accounts-http \
       --global

# Add backend as a link to classifier instance group
gcloud compute backend-services add-backend accounts-backend \
       --project=$PROJECT \
       --instance-group=accounts-mig \
       --instance-group-zone=$ZONE \
       --balancing-mode=RATE \
       --max-rate=200 \
       --global

gcloud compute url-maps add-path-matcher $LOAD_BALANCER \
       --path-matcher-name=accounts-paths \
       --existing-host=phoenix.arxiv.org \
       --default-service=browse-backend \
       --delete-orphaned-path-matcher \
       --path-rules='/login=accounts-backend,/login/*=accounts-backend,/logout=accounts-backend,/logout/*=accounts-backend'

# If the load balancer doesn't work after about 60 sec.
# to to the GCP UI, go to load balancer, go to the load balancer that
# this script creates, click edit, click finalize and then save (or update)
