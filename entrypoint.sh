#!/bin/bash
echo "::group::Authenticate to cluster"
if [[ -f .env ]]
then
  export $(grep -v '^#' .env | xargs)
  if [[ $? != 0 ]]
  then
    echo "[$(date +"%m/%d/%y %T")] An error occured during import .env variables (Reason: unknown)"
    exit 1
  fi
  echo "[$(date +"%m/%d/%y %T")] Exported all env variables"
else 
  echo "[$(date +"%m/%d/%y %T")] An error occured during import .env variables (Reason: no .env file found)"
  exit 1
fi

# Create the KUBECONFIG to be authenticated to cluster
echo "Creation of the KUBECONFIG and connection to the cluster $CLUSTER_NAME"
aws eks --region eu-west-1 update-kubeconfig --name $CLUSTER_NAME

if [[ $? == 1 ]]
then
  echo "[$(date +"%m/%d/%y %T")] An error occured during creation of kubeconfig or connection to cluster $CLUSTER_NAME"
  exit 1
fi
echo "[$(date +"%m/%d/%y %T")] Authenticated to cluster with success"
echo "::endgroup::"

## Launches Metaflow for model deployment
echo "::group::Metaflow auto-model-deployment"
make argo




echo "::endgroup::"

## Launches loki tests
MODEL_INSTANCE_ID="$INPUT_MODELINSTANCEID"
WORFLOW_TEMPLATE_NAME="$INPUT_WORKFLOWTEMPLATENAME"
REGRESSION_TEST_ID="non-regression-${MODEL_INSTANCE_ID}-$(date +"%s")"
if [[ -z $MODEL_INSTANCE_ID || $MODEL_INSTANCE_ID == "" || $INPUT_MODELINSTANCEID == "" ]]
then
  echo "[$(date +"%m/%d/%y %T")] Error: missing MODEL_INSTANCE_ID env variable"
  exit 1
elif [[ -z $WORFLOW_TEMPLATE_NAME ]]
then
  echo "[$(date +"%m/%d/%y %T")] Error: missing WORFLOW_TEMPLATE_NAME env variable"
  exit 1
fi

WORKFLOW_NAME=$(argo submit --from $WORFLOW_TEMPLATE_NAME -w -p test_id=$REGRESSION_TEST_ID -p model_instance_id=$MODEL_INSTANCE_ID -p test_file_location_id=$LOKI_FILE_LOCATION_ID -p environment=$WORKER_ENV -p inarix_api_hostname=$API_ENDPOINT -p prediction_entrypoint=$PREDICTION_ENDPOINT  -o json | jq -e -r .metadata.name)