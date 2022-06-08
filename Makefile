.PHONY: init argo argo-deploy clean local

init: requirements.txt
	@pip install -r requirements.txt

local: init
	@python bookish.py run

argo-deploy: 
	METAFLOW_KUBERNETES_SERVICE_ACCOUNT=argo-workflow METAFLOW_DATASTORE_SYSROOT_S3="s3://loki-artefacts/metaflow/" python bookish.py --datastore=s3 argo-workflows create

argo: clean argo-deploy
	METAFLOW_KUBERNETES_SERVICE_ACCOUNT=argo-workflow METAFLOW_DATASTORE_SYSROOT_S3="s3://loki-artefacts/metaflow/" python bookish.py --datastore=s3 argo-workflows trigger --env_file .env

clean:
	rm -rf __pycache__