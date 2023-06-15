import json
import os
import subprocess
from abc import abstractmethod

from cumulusci.core.config import ScratchOrgConfig
from cumulusci.tasks.sfdx import SFDXBaseTask
from cumulusci.core.exceptions import CommandException
from cumulusci.core.keychain import BaseProjectKeychain

LOAD_COMMAND = "sfdx sfdmu:run --sourceusername CSVFILE --targetusername {targetusername} -p {pathtoexportjson} --canmodify {instanceurl} --noprompt --verbose"
SCRATCHORG_LOAD_COMMAND = "sfdx sfdmu:run --sourceusername CSVFILE --targetusername {targetusername} -p {pathtoexportjson} --noprompt --verbose"


class SFDMULoad(SFDXBaseTask):
    task_docs = """
    Custom Task for Running Data Uploads with the SFDMU Plugin.
    """

    keychain_class = BaseProjectKeychain
    task_options = {
        "pathtoexportjson": {
            "description": "Directory path to the export.json to upload",
            "required": True
        },
        "targetusername": {
            "description": "Username or AccessToken of the account that will be used to upload the data",
            "required": False
        },
        "instanceurl": {
            "description": "Instance url for the targetusername.",
            "required": False
        },
        "accesstoken": {
            "description": "Passed in accesstoken associated to the targetusername and instance url.",
            "required": False
        },
        "org": {
            "description": "Value to replace every instance of the find value in the source file.",
            "required": False
        }
    }

    def _prepareexportjsonfile(self):

        if not os.path.isdir(self.pathtoexportjson):
            raise Exception("Path to export.json is not valid")

        if not os.path.isfile(f"{self.pathtoexportjson}/export.json"):
            raise Exception("export.json is missing")

        with open(f"{self.pathtoexportjson}/export.json", "r") as tmpFile:
            defcontents = tmpFile.read()
            tmpFile.close()

            exportjson = json.loads(defcontents)

            # build the org data
            orgdata = {'name': self.targetusername, 'accessToken': self.accesstoken, 'instanceUrl': self.instanceurl}

            exportjson["orgs"] = []
            exportjson["orgs"].append(orgdata)

            tmpdata = json.dumps(exportjson)

            self.logger.info('Formatted EXPORT.JSON:' + tmpdata)

        with open(f"{self.pathtoexportjson}/export.json", "w") as tmpFile:
            tmpFile.write(tmpdata)
            tmpFile.close()

    def _cleanupexportjsonfile(self):
        if os.path.isdir(self.pathtoexportjson):
            if os.path.isfile(f"{self.pathtoexportjson}/export.json"):
                with open(f"{self.pathtoexportjson}/export.json", "r") as tmpFile:
                    defcontents = tmpFile.read()
                    tmpFile.close()
                    exportjson = json.loads(defcontents)
                    exportjson["orgs"] = []
                    tmpdata = json.dumps(exportjson)

                    with open(f"{self.pathtoexportjson}/export.json", "w") as tmpFile:
                        tmpFile.write(tmpdata)
                        tmpFile.close()

    def _setprojectdefaults(self, instanceurl):
        subprocess.run([f"sfdx config:set instanceUrl={instanceurl}"], shell=True, capture_output=True)

    def _init_options(self, kwargs):
        super(SFDMULoad, self)._init_options(kwargs)
        self.env = self._get_env()

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

    def _prepruntime(self, a):

        if ("org" in self.options and not self.options["org"] is None) and self.keychain is None:
            self._load_keychain()
            self.logger.info("Org passed in but no keychain found in runtime")

        # location of the export.json
        if "pathtoexportjson" not in self.options or not self.options["pathtoexportjson"]:
            self.pathtoexportjson = "datasets/sfdmu/"
        else:
            self.pathtoexportjson = self.options["pathtoexportjson"]

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

    def _run_task(self):

        self._prepruntime(self)
        self._setprojectdefaults(self.instanceurl)
        self._prepareexportjsonfile()
        self.logger.info('Target Path:' + self.pathtoexportjson)
        self.logger.info('Current Working Directory:' + self.options.get("dir"))
        self.options["command"] = self._get_command()
        output = []

        cmdtorun = self._get_command()
        resp = subprocess.run([f"{cmdtorun}"], shell=True, capture_output=True, cwd=self.options.get("dir"))

        # resp = output[0].decode("utf-8")
        stdoutres = resp.stdout.splitlines()
        [self.logger.info(i) for i in stdoutres]
        # self.logger.info(resp.stdout)

        self.logger.info('cleaning up export.json..')
        self._cleanupexportjsonfile()

    def _get_command(self):
        command = ""
        if not isinstance(self.org_config, ScratchOrgConfig):
            command = LOAD_COMMAND.format(
                pathtoexportjson=self.pathtoexportjson,
                instanceurl=self.instanceurl.replace("https://", ""),
                targetusername=self.targetusername
            )
        else:
            command = SCRATCHORG_LOAD_COMMAND.format(
                pathtoexportjson=self.pathtoexportjson,
                targetusername=self.targetusername
            )

        return command

    def _handle_returncode(self, returncode, stderr):
        if returncode:
            message = "Return code: {}".format(returncode)
            if stderr:
                message += "\nstderr: {}".format(stderr.read().decode("utf-8"))
            self.logger.error(message)
            raise CommandException(message)
