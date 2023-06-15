from abc import ABC
from cumulusci.core.tasks import BaseTask
from cumulusci.core.config import ScratchOrgConfig
from qbrix.tools.shared.qbrix_console_utils import init_logger

log = init_logger()


class RunLanding(BaseTask, ABC):
    task_docs = """
    Runs Post Deployment checks and deployments for target Salesforce orgs.

    Supports information only mode where no tasks are executed. Use the command cci task run qbrix_landing --info_mode True --org OrgAliasHere
    """

    task_options = {
        "info_mode": {
            "description": "Set to True if you just want to see what tasks this will run, without running them.",
            "required": False
        },
        "org": {
            "description": "org alias",
            "required": False
        }
    }

    salesforce_task = True

    def _init_options(self, kwargs):
        super(RunLanding, self)._init_options(kwargs)
        self.scratch_org_mode = False
        self.info_mode = self.options["info_mode"] if "info_mode" in self.options else False

    def scratch_org_tasks(self):
        pass

    def production_org_tasks(self):
        pass

    def shared_tasks(self):
        pass

    def _run_task(self):

        log.info("Starting QBrix Post-Deployment Checks")

        if self.info_mode:
            log.info("*** RUNNING AS INFORMATION MODE - NO TASKS WILL ACTUALLY BE RUN ***")

        self.scratch_org_mode = True if isinstance(self.org_config, ScratchOrgConfig) else False

        self.shared_tasks()

        if self.scratch_org_mode:
            log.info("Running in Scratch Org Mode")
            self.scratch_org_tasks()
        else:
            log.info("Running in Production Org Mode")
            self.production_org_tasks()

        log.info("Q Brix Post-Deploy Checks Complete")
