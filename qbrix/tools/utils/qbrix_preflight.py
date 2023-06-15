import json
import os
from abc import ABC

import requests
from cumulusci.core.exceptions import CommandException
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.tasks import BaseTask
from cumulusci.core.config import ScratchOrgConfig, TaskConfig
from qbrix.tools.shared.qbrix_console_utils import init_logger
from qbrix.salesforce.qbrix_salesforce_tasks import QbrixInstallCheck
from qbrix.tools.shared.qbrix_cci_tasks import run_cci_task, run_cci_flow
from qbrix.tools.shared.qbrix_project_tasks import run_command
from qbrix.tools.utils.qbrix_orgconfig_hydrate import NGOrgConfig

log = init_logger()


class RunPreflight(BaseTask, ABC):
    task_docs = """
    Q Brix Preflight runs multiple tasks and flows against your target org to prepare it for the main deployment. By default it deploys settings and ensures that the Q Brix Registration package is installed.
    """

    task_options = {
        "include_base_config": {
            "description": "Set to True if you want the base config and data deployed into the target org. Defaults to False",
            "required": False
        },
        "base_config_only_scratch": {
            "description": "Set to True if you want the base config and data deployed into only scratch orgs. Defaults to False",
            "required": False
        },
        "only_base_config": {
            "description": "Set to True if you only want to deploy base config and NOT base data. Defaults to False",
            "required": False
        },
        "skip_settings_deployment": {
            "description": "Set to True if you don't want preflight to deploy settings. Defaults to False",
            "required": False
        },
        "skip_hydrate": {
            "description": "Set to True if you don't want preflight to hydrate options for where clauses. Defaults to False",
            "required": False
        },
        "org": {
            "description": "The alias for the connected target org within the CumulusCI Project. Ensure that either this is provided or the access token.",
            "required": False
        }
    }

    salesforce_task = True
    keychain_class = BaseProjectKeychain

    def _init_options(self, kwargs):
        super(RunPreflight, self)._init_options(kwargs)
        
        try:
            # Initiate Shared Variables
            self.scratch_org_mode = True if isinstance(self.org_config, ScratchOrgConfig) else False

            # Initiate Options
            self.include_base_config = self.options["include_base_config"] if "include_base_config" in self.options else False
            self.base_config_only_scratch = self.options["base_config_only_scratch"] if "base_config_only_scratch" in self.options else False
            self.only_base_config = self.options["only_base_config"] if "only_base_config" in self.options else False
            self.skip_settings_deployment = self.options["skip_settings_deployment"] if "skip_settings_deployment" in self.options else False
            self.skip_hydrate = self.options["skip_hydrate"] if "skip_hydrate" in self.options else False


        except:
            print('Error on Preflight')

    def deploy_settings(self):
        
        settings_path = "force-app/main/default/settings"

        cwd = os.getcwd()
        pwd = os.getenv("PWD")

        if pwd != cwd:
            settings_path = os.path.join(cwd, settings_path)
            self.logger.info(f"Updating settings path to {settings_path}")

        # Deploy Settings if Present
        if os.path.exists(settings_path) and not self.skip_settings_deployment:
            self.logger.info("PREFLIGHT: Deploying Settings Directory from force-app/main/default/settings")
            run_command(f"cci task run deploy --path force-app/main/default/settings --org {self.org_config.name}", os.getcwd())
        else:
            self.logger.info("PREFLIGHT: Skipping Settings Deployment.")

    def deploy_qbrix_register(self):
        if not QbrixInstallCheck("QBrix-1-xDO-Tool-QBrixRegister", self.org_config):
            self.logger.info(f"PREFLIGHT: Deploying Q Brix Registration to Org {self.org_config.name}")
            checkreg_deploy_result = run_cci_task("base:check_register", self.org_config.name)
            if checkreg_deploy_result:
                self.logger.info("PREFLIGHT: Register Check Complete!")
            else:
                self.logger.info("PREFLIGHT: Register Check Failed. Check errors and warnings (if any) mentioned above.")

    def deploy_base_config_and_data(self):
        self.logger.info("Checking and loading Q Brix Base Config and Data")

        if not QbrixInstallCheck("QBrix-0-xDO-BaseConfig", self.org_config):
            self.logger.info("Installing Q Brix Base Config")
            deploy_result = run_cci_flow(f"base:deploy_qbrix", self.org_config.name)

            if deploy_result:
                self.logger.info(f"Q Brix Base Config Deployment Complete!")
            else:
                log.error(f"Q Brix Base Config Deployment Failed. Check errors and warnings (if any) mentioned above.")
        else:
            self.logger.info("Q Brix Base Config Deployed")

        if not self.only_base_config:
            if not QbrixInstallCheck("QBrix-0-xDO-BaseData", self.org_config):
                self.logger.info("Installing Q Brix Base Data")
                deploy_result = run_cci_flow(f"base:deploy_qbrix_base_data", self.org_config.name)

                if deploy_result:
                    self.logger.info(f"Q Brix Base Data Deployment Complete!")
                else:
                    log.error(f"Q Brix Base Data Deployment Failed. Check errors and warnings (if any) mentioned above.")
            else:
                self.logger.info("Q Brix Base Data Deployed")

    def scratch_org_tasks(self):
        if self.include_base_config:
            self.deploy_base_config_and_data()

    def production_org_tasks(self):
        if self.include_base_config and self.base_config_only_scratch is False:
            self.deploy_base_config_and_data()

    def shared_tasks(self):
        # Deploy Settings
        if not self.skip_settings_deployment:
            self.deploy_settings()

        # Check and deploy Q Brix Register
        self.deploy_qbrix_register()

    def _run_task(self):
        self.logger.info("PREFLIGHT: Starting Q Brix Preflight Check")

        if not self.skip_hydrate:
            self.logger.info("PREFLIGHT: Running Org Config Hydrate")
            hydrate = NGOrgConfig(
                org_config=self.org_config,
                project_config=self.project_config,
                task_config=TaskConfig({"class_path": "qbrix.tools.utils.qbrix_orgconfig_hydrate.NGOrgConfig"})
            )
            hydrate._run_task()

        self.logger.info("PREFLIGHT: Running Shared Tasks, which apply to all Orgs")
        self.shared_tasks()

        if self.scratch_org_mode:
            self.logger.info("PREFLIGHT: Running Scratch Org and Sandbox Related Tasks")
            self.scratch_org_tasks()
        else:
            self.logger.info("PREFLIGHT: Running Production Org Related Tasks")
            self.production_org_tasks()

        self.logger.info("PREFLIGHT: Preflight Complete")
