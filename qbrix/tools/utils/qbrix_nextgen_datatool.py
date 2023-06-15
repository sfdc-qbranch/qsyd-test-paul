from time import sleep
import time
import requests

from abc import ABC
from abc import abstractmethod
from cumulusci.core.tasks import BaseTask
from cumulusci.tasks.sfdx import SFDXBaseTask
from qbrix.tools.shared.qbrix_console_utils import init_logger
from cumulusci.core.config import ScratchOrgConfig
from qbrix.salesforce.qbrix_salesforce_tasks import salesforce_query
from cumulusci.core.keychain import BaseProjectKeychain


log = init_logger()


class RunDataTool(SFDXBaseTask):
    keychain_class = BaseProjectKeychain
    task_options = {
        "data_keys": {
            "description": "Data Collection Key or keys",
            "required": True
        },
        "total_timeout": {
            "description": "Total Timeout in Seconds. Defaults to 8600 seconds.",
            "required": False
        },
        "wait": {
            "description": "If defined, this is the total amount of time in seconds which the script will wait between each data load. If only one data collection is defined, this will be the wait time after the data load has completed.",
            "required": False
        },
        "org": {
            "description": "org alias",
            "required": False
        },
    }

    task_docs = """
    Takes a list of data collection IDs which are then deployed using the NextGen Data Tool. At least one data collection ID must be specified.
    """
    
    @property
    def keychain_cls(self):
        klass = self.get_keychain_class()
        return klass or self.keychain_class

    @abstractmethod
    def get_keychain_class(self):
        return None

    @property
    def keychain_key(self):
        return self.get_keychain_key()

    @abstractmethod
    def get_keychain_key(self):
        return None

    def _load_keychain(self):
        if self.keychain is not None:
            return

        keychain_key = self.keychain_key if self.keychain_cls.encrypted else None

        if self.project_config is None:
            self.keychain = self.keychain_cls(self.universal_config, keychain_key)
        else:
            self.keychain = self.keychain_cls(self.project_config, keychain_key)
            self.project_config.keychain = self.keychain

    def _prepruntime(self):

        if ("org" in self.options and not self.options["org"] is None) and self.keychain is None:
            self._load_keychain()
            self.logger.info("Org passed in but no keychain found in runtime")

        if not self.org_config.access_token is None:
            self.accesstoken = self.org_config.access_token

        if not self.org_config.instance_url is None:
            self.instanceurl = self.org_config.instance_url
            
    def _init_options(self, kwargs):
        super(RunDataTool, self)._init_options(kwargs)
        self.env = self._get_env()
        self.url = "https://nxdo-data-tool.herokuapp.com/api/jobs/deployment"
        self.data_keys = self.options["data_keys"]
        self.total_timeout = int(self.options["total_timeout"]) if "total_timeout" in self.options else 8600
        self.wait = int(self.options["wait"]) if "wait" in self.options else 2

    def _run_task(self):

        self._prepruntime()
        self.logger.info("NextGen Data Tool: Starting Data Load")

        if not self.data_keys:
            self.logger.error(
                "NextGen Data Tool: Error, there were no data collection keys were passed! Please check your task definition and add the correct data keys.")
            raise Exception("No Data Keys Passed! Data Load Failed.")

        data_load_job_counter = 1
        total_keys = len(self.data_keys)

        # Get Email from target org
        email_address = salesforce_query(
            f"SELECT Email From User Where Username = '{self.org_config.username}' LIMIT 1", self.org_config)
        if email_address is None or email_address == "":
            raise Exception("Unable to get email address from the target org. Stopping Data Load.")

        # Get Org Type
        IsScratchOrg = True if isinstance(self.org_config, ScratchOrgConfig) else False
        if self.org_config.is_sandbox:
            IsScratchOrg = True

        for data_key in self.data_keys:

            # Set Start Time of Job
            st = time.time()
            self.logger.info(f"NextGen Data Tool: Processing Data Load {data_load_job_counter} of {total_keys}")

            # Check for missing Data Collection Key
            if data_key is None or data_key == "":
                self.logger.error(
                    f"NextGen Data Tool: Invalid or missing Data Collection ID. Skipping Job {data_load_job_counter} of {total_keys}.")
                continue

            # Start Data Load and get Job ID
            headers = {"Content-Type": "application/json; charset=utf-8"}
            data = {
                "username": self.org_config.username,
                "email": email_address,
                "collection_version_id": f"{data_key}",
                "is_production": not IsScratchOrg,
                "instance_url": self.instanceurl,
                "access_token": self.accesstoken
            }
            
            #self.logger.info(data)

            self.logger.info(
                f"NextGen Data Tool: Starting Job\n\nRequesting Data Job with the following configuration:\n\nData Collection ID: {data_key}\nUsername: {self.org_config.username}\nEmail: {email_address}\nScratch Org Mode: {IsScratchOrg}\n")
            result = requests.post(self.url, json=data, headers=headers)
            jsonResponse = result.json()

            if jsonResponse is not None:
                job_id = jsonResponse["id"]
                self.logger.info(f"NextGen Data Tool: Data Load started with ID {job_id}")
            else:
                self.logger.error(
                    f"NextGen Data Tool: Error the job failed to start. This could be due to network issues or issues with the NextGen Data Load host.")
                raise Exception("Data Load Job Failed to start.")

            job_status_check_url = f"{self.url}/{job_id}"

            # Check job for status updates
            timeout = 0
            total_retries = 0

            if self.total_timeout < 500 or self.total_timeout > 8600:
                self.total_timeout = 8600

            self.logger.info(f'JOB STATUS URL:: {job_status_check_url}')
            while True:

                # Get Job Status
                check_job = requests.get(job_status_check_url)

                # print("\nResult\n")
                # print(check_job.json())

                # Handle issues with job status
                if check_job.json() is None:
                    if total_retries > 3:
                        self.logger.error("NextGen Data Tool: Unable to lookup job status. Check your internet connection.")
                        raise Exception("NextGen Data Tool Job Failed")
                    else:
                        total_retries += 1
                        log.debug(
                            f"NextGen Data Tool: Unable to lookup job status. Waiting 5 seconds and then retrying... retry attempt {total_retries}")
                        sleep(5)
                        continue

                # Handle Timeout
                if timeout > self.total_timeout:
                    self.logger.error(
                        f"NextGen Data Tool: Error Data Load Timeout Reached (Timeout set at {self.total_timeout} seconds)")
                    raise Exception("Data Load timed out. Data load failed.")

                check_job_json = check_job.json()
                
                #self.logger.info(check_job_json)
                
                status = check_job_json["state"]
                progress = check_job_json["progress"]
                status_update = "Waiting to start."

                if isinstance(progress, dict):
                    status_update = f"Running - {progress['progress']}%"

                if status == "completed":
                    et = time.time()
                    elapsed_time = et - st
                    self.logger.info(f"Job Complete! Total Time: " + time.strftime("%H:%M:%S", time.gmtime(elapsed_time)))
                    break

                if status == "active":
                    self.logger.info(f"NextGen Data Tool: Job ID {job_id}. {status_update}")

                if status == "failed":
                    self.logger.error(f"The data load job has failed. Job ID: {job_id}")
                    self.logger.error(check_job_json)
                    raise Exception("Data Load Failed")

                if status != "active" and status != "completed":
                    self.logger.error(f"NextGen Data Tool: Unsupported status ({status}) read. Stopping deployment")
                    raise Exception("Data Load Failed. An unsupported status was received from the NextGen Data Tool.")

                sleep(5)
                timeout += 1

            data_load_job_counter += 1
            sleep(self.wait)
