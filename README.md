# ga-model-deployment

**Version:** v2.0.1

## Table of contents

1. [Getting started](#getting-started)
2. [Changelog](#changelog)
3. [License](#license)

## Getting started
### .env configuration (**Required**)
As **REQUIRED** by the script, several ENV variables (which are handled automatically by github in GithubAction cases) needs to be provided. The best option is to create a `.env` file with the following variables (remove comments):

**Warning** Please avoid use doubled quotes `(e.g "example value")` on `.env` file, simply provide the value right after the `=` sign. As the script might failed

**Considering** you have your aws cli installed and configured with storage access `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` does not have to be provided in .env

```.env
WORKER_ENV=production
NUTSHELL_MAX_CROP=4000
NUTSHELL_MODE=worker
NUTSHELL_MODEL_SERVING_NAME=exported-barley-protein-v1-22-1-devops
NUTSHELL_WORKER_MODEL_FILE_LOC_ID=1957034
NUTSHELL_WORKER_MODEL_PREDICT_TIMEOUT_S=60
NUTSHELL_MODEL_VERSION=v1.22.1-devops
NUTSHELL_LISTENING_PORT=8080
NUTSHELL_MODEL_PATH=gs://inarix-models/export/XXX
NUTSHELL_MODEL_CONFIG=''
LABEL_TEMPLATE_SLUG=barley_variety_predicted_v7
SHARED_CACHE_PATH=/mnt/filestore
MODEL_TEMPLATE_ID=15
EXPORTED_MODEL_ID=834309eb-e11c-4f2c-82cf-5139072d5eca
LOKI_FILE_LOCATION_ID=1957033
GOOGLE_APPLICATION_CREDENTIALS=/app/client_secrets.json
MODEL_HELM_CHART_VERSION=2.5.1
GITHUB_REPOSITORY=inarix/mt-XX
ARGOCD_ENTRYPOINT=https://argocd.inarix.com/api/v1
ARGOCD_TOKEN=""
```

### Launching Metaflow run on local machine
The main entrypoint is the cli-compatible bookish.py
You can simply launch a model deployment scenario with the following syntax: `make local`

### Launching Metaflow run on ArgoWorkflows
As I wanted it to be ran ASAP since this could be used for :fire::fire: reasons, I used the `make argo`

## Changelog

SEE CHANGELOG IN [CHANGELOG.md](CHANGELOG.md)

## Annexes
[1. Metaflow documentation](https://docs.metaflow.org/metaflow/basics)

[2. Config documentation on code](https://github.com/Netflix/metaflow/blob/6cdd311bdbed274f0b5c75b153699d32409cee1f/metaflow/metaflow_config.py#L16)