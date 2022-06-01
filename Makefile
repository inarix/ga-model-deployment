init:
	pip install -r requirements.txt

local: 
	python bookish.py run

argo-deploy: 
	METAFLOW_KUBERNETES_SERVICE_ACCOUNT=argo-workflow METAFLOW_DATASTORE_SYSROOT_S3="s3://loki-artefacts/metaflow/" python bookish.py --datastore=s3 argo-workflows create

argo: argo-deploy
	METAFLOW_KUBERNETES_SERVICE_ACCOUNT=argo-workflow METAFLOW_DATASTORE_SYSROOT_S3="s3://loki-artefacts/metaflow/" python bookish.py --datastore=s3 argo-workflows trigger --env_file .env



.PHONY: init local argo argo-deploy
