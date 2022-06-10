"""
ModelDeployment module will be used for Auto model deployment.
This is meant to be used with Github Action, or locally when
in fact GithubAction is down, or unaccessible.
"""
import os
import time
from metaflow import FlowSpec, step, IncludeFile, S3
from requests.exceptions import HTTPError

def generate_app_model_name(repo_name: str, model_version:str) -> str:
    model_name = repo_name.split("/")[1]
    return f"{model_name}-{model_version.replace('.', '-')}"

def script_path(filename):
    """
    A convenience function to get the absolute path to a file in this
    tutorial's directory. This allows the tutorial to be launched from any
    directory.
    """
    filepath = os.path.join(os.path.dirname(__file__))
    return os.path.join(filepath, filename)

def metadata_filter(obj):
    """
    Used for metadata in API model instance to not provide any credentials or unwanted values
    """
    print("metadata_filter::obj=",obj)
    return "TMP_" not in obj[0]

class ModelDeployment(FlowSpec):
    """
        ModelDeployment class is used for auto model deployment
    """

    env_file = IncludeFile(
            name="env_file",
            required=False,
            is_text=True,
            help=".env file to use for ArgoCD application creation",
            default=script_path(".env")
    )

    @step
    def start(self):
        """
        Entrypoint funtion to start model deployment
        This creates env variables dict to be used
        """
        os.system("pip install slackclient==2.9.4")
        self.env_vars = dict([x.strip().split('=') for x in self.env_file.split("\n") if '=' in x])

        self.model_version: str = self.env_vars.get("NUTSHELL_MODEL_VERSION") or ""
        self.model_name: str = generate_app_model_name(self.env_vars.get("GITHUB_REPOSITORY"), self.model_version)[3:]
        self.application_name: str = f"mt-{self.model_name}" or ""
        self.applied_repo = self.env_vars.get("GITHUB_REPOSITORY").split("/")[1]

        self.env_vars["MODEL_NAME"] = self.model_name
        self.env_vars["MODEL_VERSION"] = self.model_version
        self.env_vars["APPLICATION_NAME"] = self.application_name

        self._workerEnv = self.env_vars.get("WORKER_ENV") or ""
        self._argocdToken = self.env_vars.get("TMP_ARGOCD_TOKEN") or ""
        self._apiToken = self.env_vars.get("TMP_API_TOKEN") or ""
        self._slack_channel_id = "C01LL4VRDKL"
        from slack.web.client import WebClient
        self._slack = WebClient(token=self.env_vars.get("TMP_SLACK_API_TOKEN"))

        self._thread_ts = self._send_slack_message(
            f"[MODEL_DEPLOYMENT]: Metaflow deployment for {self.model_name}")

        self.next(self.check_inputs)

    def _send_slack_message(self, msg: str, thread_ts: str = "") -> str:
        """
        Send slack message
        """
        from slack.errors import SlackApiError
        try:
            response = None
            if thread_ts != "":
                response = self._slack.chat_postMessage(
                    channel=self._slack_channel_id, text=msg, thread_ts=thread_ts)
            else:
                response = self._slack.chat_postMessage(
                    channel=self._slack_channel_id, text=msg)
            return response.get("ts")
        except SlackApiError as e:
            assert e.response["ok"] is False
            # str like 'invalid_auth', 'channel_not_found'
            assert e.response["error"]
            if e.response["error"] == "ratelimited":
                # The `Retry-After` header will tell you how long to wait before retrying
                delay = int(e.response['headers']['Retry-After'])
                print(f"Rate limited. Retrying in {delay} seconds")
                time.sleep(delay)
                return self._send_slack_message(msg, thread_ts)
            print(f"_send_slack_message got an error: {e.response['error']}")

    def check_sha(self, is_production: bool, model_version: str) -> bool:
        """
        Check model_version to always complains the requirements
        """
        if is_production:
            return True
        if len(model_version) <= 8:
            self._send_slack_message("MODEL_VERSION should never be more than 8 chars", self._thread_ts)
            return False
        sha_only = model_version.split("-")[1]
        if len(sha_only) < 6:
            self._send_slack_message(f"SHA({sha_only}) should always have 6 chars", self._thread_ts)
            return False
        return True

    @step
    def check_inputs(self):
        """
        Checks inputs before lauching argo_application_creation function
        """
        os.system("pip install slackclient==2.9.4")
        if "WORKER_ENV" not in self.env_vars:
            raise EnvironmentError(
                "WORKER_ENV is neither in .env nor env variables")
        elif "TMP_ARGOCD_ENTRYPOINT" not in self.env_vars:
            raise EnvironmentError(
                "TMP_ARGOCD_ENTRYPOINT is neither in .env nor env variables")
        elif "TMP_ARGOCD_TOKEN" not in self.env_vars:
            raise EnvironmentError(
                "TMP_ARGOCD_TOKEN is neither in .env nor env variables")
        elif "NUTSHELL_MODEL_VERSION" not in self.env_vars:
            raise EnvironmentError(
                "NUTSHELL_MODEL_VERSION is neither in .env nor env variables")
        elif "MODEL_HELM_CHART_VERSION" not in self.env_vars:
            raise EnvironmentError(
                "MODEL_HELM_CHART_VERSION is neither in .env nor env variables")
        elif "NUTSHELL_MODEL_PATH" not in self.env_vars:
            raise EnvironmentError(
                "NUTSHELL_MODEL_PATH is neither in .env nor env variables")

        self._send_slack_message("All required env variable have been found in provided env file", self._thread_ts)
        print("Now checking for SHA in MODEL_VERSION")
        if not self.check_sha(self._workerEnv == "production", self.model_version):
            raise RuntimeError("SHA does not match the requirements")
        print("SHA version is complient")
        self.next(self.argo_application_creation)

    def waitForHealthy(self):
        os.system("pip install slackclient==2.9.4")
        import requests
        endpoint = self.env_vars.get("TMP_ARGOCD_ENTRYPOINT")
        token = self._argocdToken
        name = self.application_name
        max_retry = int(os.environ.get("INPUT_MAXRETRY", "10"))
        tts = int(os.environ.get("INPUT_TTS", "5"))
        headers = {"Authorization": f"Bearer {token}"}
        while True and max_retry > 0:
            res = requests.get(f"{endpoint}/{name}", headers=headers)
            if res.status_code != 200:
                raise RuntimeError(
                    f"error: Status code != 200, {res.status_code}")
            payload = res.json()
            if ("status" in payload) and ("health" in payload["status"]) and ("status" in payload["status"]["health"]):
                status = payload["status"]["health"]["status"]
                if status == "Healthy":
                    print("Application is now Healthy")
                    return
                elif status == "Missing" or status == "Degraded":
                    print(
                        f"Health status error: {status} then retry {max_retry}")
                    max_retry -= 1
                elif status != "Progressing":
                    raise RuntimeError(f"Final Health status error: {status}")
                else:
                    print(f"StateUpdate: Application is in status {status}")
            else:
                raise RuntimeError("Invalid payload returned from ArgoCD")

            print(f"Waiting for {tts}s")
            time.sleep(tts)

    def checkApplicationExists(self) -> bool:
        os.system("pip install requests")
        import requests
        argocd_entrypoint: str = self.env_vars.get("TMP_ARGOCD_ENTRYPOINT") or ""
        token: str = self._argocdToken or ""
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(
                url=f"{argocd_entrypoint}/{self.application_name}",
                headers=headers
                )
        if res.status_code == 200:
            return True
        elif res.status_code == 404:
            return False
        else:
            res.raise_for_status()
            return False

    def generateArgoApplicationSpec(self) -> dict:
        node_selector = "nutshell"
        chart_version = self.env_vars.get("MODEL_HELM_CHART_VERSION")
        server_dest = "https://34.91.136.161"

        metadata = {"name": self.application_name, "namespace": "default"}

        helm = {"parameters": [
            {"name": "app.env", "value": self._workerEnv},
            {"name": "image.imageName", "value": self.applied_repo},
            {"name": "image.version", "value": self.model_version[1:]},
            {"name": "model.modelName", "value": self.model_name},
            {"name": "model.nutshellName", "value": self.model_name},
            {"name": "nodeSelector.name", "value": node_selector},
            {"name": "nutshell.worker.env", "value": self._workerEnv},
            {"name": "model.servingMode", "value": self.env_vars.get("NUTSHELL_MODE")},
            {"name": "model.templateSlug", "value": self.env_vars.get("LABEL_TEMPLATE_SLUG")},
            {"name": "nutshell.fileLocationId", "value": self.env_vars.get( "NUTSHELL_WORKER_MODEL_FILE_LOC_ID")},
            {"name": "nutshell.timeoutS", "value": self.env_vars.get( "NUTSHELL_WORKER_MODEL_PREDICT_TIMEOUT_S")},
            {"name": "model.path", "value": self.env_vars.get( "NUTSHELL_MODEL_PATH")}
        ]}

        source = {"repoURL": "https://charts.inarix.com", "targetRevision": chart_version, "helm": helm, "chart": "inarix-serving"}
        specs = {"metadata": metadata, "spec": {"project": "model-serving", "source": source, "destination": {
            "server": server_dest, "namespace": self._workerEnv} } }
        return specs

    @step
    def argo_application_creation(self):
        """
        Create argo application
        """
        os.system("pip install slackclient==2.9.4")
        if self.checkApplicationExists():
            self._send_slack_message("Application already exists and cannot be created again", self._thread_ts)
            raise RuntimeError(
                f"{self.application_name} already exists and cannot be created again")

        import requests
        specs = self.generateArgoApplicationSpec()

        token = self._argocdToken
        endpoint = self.env_vars.get("TMP_ARGOCD_ENTRYPOINT")
        headers = {"Authorization": f"Bearer {token}"}
        creation_response = requests.post(f"{endpoint}", json=specs, headers=headers)

        if creation_response.status_code != 200:
            resp_json = creation_response.json()
            raise HTTPError(f"error: {resp_json['error']}")

        self._send_slack_message("Application has been created and will now be synced", self._thread_ts)

        self.next(self.sync_application)

    @step
    def sync_application(self):
        """
        Sync selected Application to ArgoCD
        """
        os.system("pip install slackclient==2.9.4")
        import requests
        token = self._argocdToken
        endpoint = self.env_vars.get("TMP_ARGOCD_ENTRYPOINT")
        headers = {"Authorization": f"Bearer {token}"}
        print(f"Syncing {self.application_name}")
        resp = requests.post(
            f"{endpoint}/{self.application_name}/sync", headers=headers)
        if resp.status_code != 200:
            resp_json = resp.json()
            raise HTTPError(f"error: {resp_json['error']}")

        self._send_slack_message("Application has been synced with success", self._thread_ts)
        self._send_slack_message("Waiting for it to be Healthy", self._thread_ts)

        self.waitForHealthy()

        self._send_slack_message("Application is now Healthy", self._thread_ts)
        self.next(self.register_model_to_api)

    @step
    def register_model_to_api(self):
        """
        Register Nutshell Application as a new model template in the inarix-api
        """
        os.system("pip install slackclient==2.9.4")
        self.env_vars["ci"] = {"source": "Github Action",
                               "provider": "Metaflow", "path": __file__}
        model_template_id = self.env_vars.get("MODEL_TEMPLATE_ID")
        project_id = self.env_vars.get("GOOGLE_PROJECT_ID")

        token = self._apiToken
        host_endpoint = self.env_vars.get("TMP_INARIX_HOSTNAME")
        endpoint = f"https://{host_endpoint}/imodels/model-instance"
        headers = {"Authorization": f"Bearer {token}"}
        metadata = filter(metadata_filter, self.env_vars)
        model_registration_payload = {"templateId": int(model_template_id), "branchSlug": self._workerEnv, "version": f"{self.model_version}",
                                      "dockerImageUri": f"eu.gcr.io/{project_id}/{self.applied_repo}:{self.model_version}-staging", "isDeployed": True, "metadata": metadata}

        import requests
        resp = requests.post(endpoint, headers=headers, json=model_registration_payload)
        resp_json = resp.json()
        if resp.status_code != 201:
            print("resp", resp_json)
            msg = resp_json["message"]
            internalCode = resp_json["data"]["internalCode"]
            err = f"HTTP/{resp.status_code} at {internalCode}, {msg}"
            self._send_slack_message(err, thread_ts=self._thread_ts)
            raise HTTPError(f"An API error occured: {err}")

        if "id" not in resp_json:
            raise RuntimeError("There is no id key in resp_json.")

        self._model_instance_id = resp_json["id"]
        self.next(self.end)

    @step
    def end(self):
        """
        ending step
        """
        os.system("pip install slackclient==2.9.4")
        self._send_slack_message(
            f"{self.model_name} has been registered to inarix-api with id {self._model_instance_id}!", self._thread_ts)

        run_id=os.environ.get("ARGO_WORKFLOW_NAME")
        with S3(s3root=f's3://loki-artefacts/metaflow/modelInstanceIds/{run_id}') as s3:
            url = s3.put('modelInstanceId', self._model_instance_id)
            url = s3.put('threadTS', self._thread_ts)
            print(f"ModelInstanceId({self._model_instance_id}) file is saved at = {url}")

if __name__ == '__main__':
    ModelDeployment(use_cli=True)
