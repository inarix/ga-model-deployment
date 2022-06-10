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

echo "::group::ArgoWorkflow list"
argo list
echo "::endgroup::"

## Launches Metaflow for model deployment
if [[ $INPUT_SKIPDEPLOYMENT == 0 ]]
then
  echo "::group::Metaflow auto-model-deployment"
  function fromArgoToWorkflowId { 
    # As $() run in a subshell, /app is lost as subshell starts at root
    cp .env /app
    cd /app
    make argo >>output.tmp 2>&1
    INPUT=$(cat output.tmp | tail -n1)
    python3 -c "
    import re
    import sys
    input= sys.argv[1]
    input= re.findall('\((.*?)\)',input)[0]
    splitted=input.split(' ')[1].lstrip('argo-')
    print(splitted)
    " "$INPUT"
    if [[ $? == 1 ]]
    then
      echo "An error occured while fetching Workflow id:"
      cat output.tmp
      exit 1
    fi
    cd -
  }

  echo "[$(date +"%m/%d/%y %T")] Launch model deployment"
  WORKFLOW_MODEL_DEPLOY_ID=$(fromArgoToWorkflowId)
  echo "[$(date +"%m/%d/%y %T")] Display output.tmp"
  cat output.tmp
  echo "[$(date +"%m/%d/%y %T")] Waiting..."
  argo wait $WORKFLOW_MODEL_DEPLOY_ID
  if [[ $? == 1 ]]
  then
    echo "[$(date +"%m/%d/%y %T")] ArgoWorkflow failed"
    exit 1
  fi

  URI_MODEL_INSTANCE_ID="s3://loki-artefacts/metaflow/modelInstanceIds/$WORKFLOW_MODEL_DEPLOY_ID/modelInstanceId"
  URI_THREAD_TS="s3://loki-artefacts/metaflow/modelInstanceIds/$WORKFLOW_MODEL_DEPLOY_ID/threadTS"
  echo "[$(date +"%m/%d/%y %T")] Downloading ModelInstance id from $URI"
  aws s3 cp $URI_MODEL_INSTANCE_ID ./modelInstanceId
  aws s3 cp $URI_THREAD_TS ./threadTS
  MODEL_INSTANCE_ID=$(cat modelInstanceId)
  THREAD_TS=$(cat threadTS)
  echo "::endgroup::"
fi

## Launches loki tests
echo "::group::Loki non-regression tests"
if [[ $INPUT_SKIPDEPLOYMENT == 1 ]]
then
  MODEL_INSTANCE_ID="$INPUT_MODELINSTANCEID"
fi

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

PREDICTION_ENDPOINT="https://${API_ENDPOINT}/imodels/predict"
echo "[$(date +"%m/%d/%y %T")] Adding arguments inarix_api_hostname: $API_ENDPOINT"
WORKFLOW_NAME=$(argo submit --from $WORFLOW_TEMPLATE_NAME -w -p test_id=$REGRESSION_TEST_ID -p model_instance_id=$MODEL_INSTANCE_ID -p test_file_location_id=$LOKI_FILE_LOCATION_ID -p environment=$WORKER_ENV -p inarix_api_hostname=$API_ENDPOINT -p prediction_entrypoint=$PREDICTION_ENDPOINT  -o json | jq -e -r .metadata.name)
LOGS=$(argo logs $WORKFLOW_NAME --no-color)

# For the moment we do not remove container names
# TRAILED_LOGS=$(echo -n $LOGS | tail -n +2 | while read line; do; echo $($line | cut -d ':' -f2-) ; done )

# echo "TRAILED_LOGS=${TRAILED_LOGS}"
HAS_SUCCEED=$(echo -n "${LOGS}" | tail -n3 | head -n1 | cut -d : -f2- | tr -d ' ')

# -- Remove line breaker before sending values (Required by GithubAction)  --
LOGS="${LOGS//$'\n'/'%0A'}"

if [[ "${HAS_SUCCEED}" == "TEST_HAS_FAILED" ]]
then
  echo "::set-output name=results::'${LOGS}'"
  echo "::set-output name=threadTS::${THREAD_TS}"
  echo "::set-output name=success::false"
elif [[ "${HAS_SUCCEED}" == "TEST_HAS_PASSED" ]]
then
  echo "::set-output name=results::'${LOGS}'"
  echo "::set-output name=threadTS::${THREAD_TS}"
  echo "::set-output name=success::true"
else
  echo "::set-output name=results::'${LOGS}'"
  echo "::set-output name=threadTS::${THREAD_TS}"
  echo "::set-output name=success::false"
fi
echo "::endgroup::"