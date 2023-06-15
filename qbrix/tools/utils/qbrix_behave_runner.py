import os
import subprocess
import keyring
from abc import abstractmethod

from cumulusci.core.config import ScratchOrgConfig
from cumulusci.tasks.command import Command
from cumulusci.core.exceptions import CommandException
from cumulusci.core.keychain import BaseProjectKeychain


class BehaveRunner(Command):
    keychain_class = BaseProjectKeychain

    task_options = {
        "feature": {
            "description": "Specific feature to run. If not provided, all features are run.",
            "required": False
        },
        "scenario": {
            "description": "Specific scenario to run. If not provided, all scenarios in the Feature are run",
            "required": False
        },
        "uploadresults": {
            "description": "Upload the results to the qbrix report bucket. True or False. ",
            "required": False,
            "default": False
        },
        "org": {
            "description": "What CCI org to run the test against.",
            "required": False
        }
    }

    def _init_options(self, kwargs):
        super(Command, self)._init_options(kwargs)

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

    def to_bool(self, x):
        return x in ("True", "true", True)

    def _prepruntime(self):

        # pass the -D data into the behave framework to mount against
        if ("org" in self.options and not self.options["org"] is None) and self.keychain is None:
            self._load_keychain()
            self.logger.info("Org passed in but no keychain found in runtime")

        # run a specific feature
        if "name" not in self.options or not self.options["name"]:
            self.name = None
        else:
            self.name = self.options["name"]

        # run a specific feature
        if "feature" not in self.options or not self.options["feature"]:
            self.feature = None
        else:
            self.feature = self.options["feature"]

        # if we want to run a specific sceanrio
        if "scenario" not in self.options or not self.options["scenario"]:
            self.scenario = None
        else:
            self.scenario = self.options["scenario"]

        # if we need to upload the results to the central bucket
        if "uploadresults" not in self.options or not self.options["uploadresults"]:
            self.uploadresults = False
        else:
            self.uploadresults = self.to_bool(self.options["uploadresults"])

        # if not passed in - fall back to the key ring data
        if "targetusername" not in self.options or not self.options["targetusername"]:

            if not isinstance(self.org_config, ScratchOrgConfig):
                self.targetusername = self.org_config.access_token
            else:
                self.targetusername = self.org_config.username
        else:
            self.targetusername = self.options["targetusername"]

        # if not passed in - fall back to the key ring data
        if "accesstoken" not in self.options or not self.options["accesstoken"]:
            self.accesstoken = self.org_config.access_token
        else:
            self.accesstoken = self.options["accesstoken"]

        # if not passed in - fall back to the key ring data
        if "instanceurl" not in self.options or not self.options["instanceurl"]:
            self.instanceurl = self.org_config.instance_url
        else:
            self.instanceurl = self.options["instanceurl"]

        if self.instanceurl[-1] == '/':
            self.instanceurl = self.instanceurl.rstrip(self.instanceurl[-1])

    def buildcommand(self):

        basecmd = f"behave -f allure_behave.formatter:AllureFormatter -o reports --no-capture --no-capture-stderr"

        if self.feature is not None:
            basecmd += f" -i {self.feature}"

        if self.scenario is not None:
            basecmd += f" -n {self.scenario}"

        if self.accesstoken is not None and self.instanceurl is not None and self.targetusername is not None:
            basecmd += f" -D accesstoken='{self.accesstoken}' -D instanceurl='{self.instanceurl}' -D username='{self.targetusername}'"

        return basecmd

    def run(self):
        # snapshot of reports
        currentreports = os.listdir("reports")
        cmd = self.buildcommand()
        print(cmd)
        process = subprocess.run([f"{cmd}"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        stdoutres = process.stdout.splitlines()
        [self.logger.info(i) for i in stdoutres]

        if self.uploadresults:

            finallist = []
            for file in os.listdir("reports"):
                if file not in currentreports:
                    finallist.append(file)

            for file in finallist:
                subprocess.run([f"python3 uploads3.py reports/{file}"], shell=True)

    def _run_task(self):
        self._prepruntime()
        self.run()

    def _handle_returncode(self, returncode, stderr):
        if returncode:
            message = "Return code: {}".format(returncode)
            if stderr:
                message += "\nstderr: {}".format(stderr.read().decode("utf-8"))
            self.logger.error(message)
            raise CommandException(message)
