#!/bin/bash
set -euvf

source config.sh

TEMPLATE="accounts-template-$(date +%Y%M%d-%H%M%S)"

#### UPDATE PROCESS ####

# create a new template with a new name
gcloud compute instance-templates create-with-container $TEMPLATE \
       --machine-type e2-small \
       --tags=allow-accounts-health-check \
       --container-image $IMAGE_URL \
       --container-env-file=env_values.txt


# change the template of the instance group
gcloud compute instance-groups managed set-instance-template accounts-mig \
       --template=$TEMPLATE \
       --zone=$ZONE

# start a rolling update of the instance group
gcloud compute instance-groups managed rolling-action start-update accounts-mig \
       --version template=$TEMPLATE \
       --max-surge 4 \
       --zone=$ZONE
