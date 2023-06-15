from genericpath import isfile
import json
import os
import time
import subprocess
import requests
from abc import abstractmethod

from cumulusci.core.config import ScratchOrgConfig
from cumulusci.tasks.sfdx import SFDXBaseTask
from cumulusci.core.exceptions import CommandException
from cumulusci.core.keychain import BaseProjectKeychain

LOAD_COMMAND = "sfdx apex run "


class BatchAnonymousApex(SFDXBaseTask):
    keychain_class = BaseProjectKeychain

    task_docs = """
    Takes one or more apex script files (defined in the filepaths option) which need to be deployed and runs them against the target org.
    """

    task_options = {

        "filepaths": {
            "description": "When mode is set to File, each file is executed in order",
            "required": False
        },
        "org": {
            "description": "Value to replace every instance of the find value in the source file.",
            "required": False
        }
    }

    def _setprojectdefaults(self, instanceurl):
        subprocess.run([f"sfdx config:set instanceUrl={instanceurl}"], shell=True, capture_output=True)

    def _init_options(self, kwargs):
        super(BatchAnonymousApex, self)._init_options(kwargs)
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

        # iterate the files
        if "filepaths" in self.options and not self.options["filepaths"] is None:

            # cast to a dictionary
            self.filepaths = self.options["filepaths"]
        else:
            self.filepaths = []
            self.logger.info("No File Paths provided")

    def _run_task(self):

        self._prepruntime(self)
        self._setprojectdefaults(self.instanceurl)

        if hasattr(self, "filepaths") and self.filepaths is not None:
            for i, v in enumerate(self.filepaths):
                if os.path.isfile(v):
                    runthiscmd = f"{LOAD_COMMAND} -f {v} -u {self.accesstoken} --json"
                    self.logger.info(f'Running Apex Script in {v}')
                    resp = subprocess.run([runthiscmd], shell=True, capture_output=True, cwd=self.options.get("dir"))
                    self.logger.info(resp.stdout)
                else:
                    self.logger.error(f"File path {v} is not a valid file")

    def _handle_returncode(self, returncode, stderr):
        if returncode:
            message = "Return code: {}".format(returncode)
            if stderr:
                message += "\nstderr: {}".format(stderr.read().decode("utf-8"))
            self.logger.error(message)
            raise CommandException(message)
        
        
class RunAnonymousApexAndWait(SFDXBaseTask):
    keychain_class = BaseProjectKeychain

    task_docs = """
    Takes one or more apex script files (defined in the filepaths option) which need to be deployed and runs them against the target org.
    """

    task_options = {

        "filepath": {
            "description": "relative file path to the apex anonymous apex to run",
            "required": False
        }
        ,
        "waitseconds": { 
            "description": "Number of secondsd to wait per cycle. Default is 60",
            "required": False
        },
        "exitonsoqlzero": { 
            "description": "SOQL Count() to verify for exit. When the count result hits 0, it exits.",
            "required": False
        },
        "maxwaithchecks": { 
            "description": "Max number of times to check to and wait after no detection of the running jobs. Each wait check is 60 seconds. Default of 1 if not set.",
            "required": False
        },
         "runscriptperwait": { 
            "description": "True or False to run an script per wait cycle",
            "required": False
        },
         "waitscript": { 
            "description": "Script file to run per wait",
            "required": False
        }
         ,
        "org": {
            "description": "Value to replace every instance of the find value in the source file.",
            "required": False
        }
    }

    def _setprojectdefaults(self, instanceurl):
        subprocess.run([f"sfdx config:set instanceUrl={instanceurl}"], shell=True, capture_output=True)

    def _init_options(self, kwargs):
        super(RunAnonymousApexAndWait, self)._init_options(kwargs)
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
        
        if "filepath" in self.options and not self.options["filepath"] is None:
            self.filepath = self.options["filepath"]
        else:
            self.filepath = None
            self.logger.info("No File Path provided")
            
        if "maxwaithchecks" in self.options and not self.options["maxwaithchecks"] is None:
            self.maxwaithchecks = self.options["maxwaithchecks"]
        else:
            self.maxwaithchecks = 1
            
        if "waitseconds" in self.options and not self.options["waitseconds"] is None:
            self.waitseconds = int(self.options["waitseconds"])
        else:
            self.waitseconds = 60
            
        if "exitonsoqlzero" in self.options and not self.options["exitonsoqlzero"] is None:
            self.exitonsoqlzero = self.options["exitonsoqlzero"]
        else:
            self.exitonsoqlzero = None
            
        if "runscriptperwait" in self.options and not self.options["runscriptperwait"] is None:
            self.runscriptperwait = bool(self.options["runscriptperwait"])
        else:
            self.runscriptperwait = False
            
        if "waitscript" in self.options and not self.options["waitscript"] is None:
            self.waitscript = self.options["waitscript"]
        else:
            self.waitscript = None

    def _run_task(self):

        self._prepruntime(self)
        self._setprojectdefaults(self.instanceurl)

        if hasattr(self, "filepath") and self.filepath is not None:
            
            if os.path.isfile(self.filepath):
                runthiscmd = f"{LOAD_COMMAND} -f {self.filepath} -u {self.accesstoken} --json"
                self.logger.info(f'Running Apex Script in {self.filepath}')
                resp = subprocess.run([runthiscmd], shell=True, capture_output=True, cwd=self.options.get("dir"))
                time.sleep(self.waitseconds)
                if hasattr(self, "exitonsoqlzero") and self.exitonsoqlzero is not None:    
                    while(self.maxwaithchecks>0):
    
                        if(self._is_zero_count(self.exitonsoqlzero)):
                            time.sleep(30)
                            if(self._is_zero_count(self.exitonsoqlzero)):
                                self.maxwaithchecks=0
                                continue
                            
                        #if we want to run a scropt per wait
                        if(self.waitscript):
                            runthiscmd = f"{LOAD_COMMAND} -f {self.waitscript} -u {self.accesstoken} --json"
                            self.logger.info(f'Running Additional Wait Apex Script in {self.waitscript}')
                            resp = subprocess.run([runthiscmd], shell=True, capture_output=True, cwd=self.options.get("dir"))
                            
                        self.maxwaithchecks=self.maxwaithchecks-1
                        time.sleep(self.waitseconds)
                            
            else:
                self.logger.error(f"File path {self.filepath} is not a valid file")
                
                
    def _is_zero_count(self,soql):
        modsoql=soql.replace(" ","+")
        url = f"{self.instanceurl}/services/data/v56.0/query/?q={modsoql}"
        headers = {
            'Authorization': f'Bearer {self.accesstoken}',
            'Content-Type': 'application/json'
        }
        response = requests.request("GET", url, headers=headers)
        data = json.loads(response.text)
        self.logger.info(data)
        return data["records"][0]["expr0"] == 0
    
    def _handle_returncode(self, returncode, stderr):
        if returncode:
            message = "Return code: {}".format(returncode)
            if stderr:
                message += "\nstderr: {}".format(stderr.read().decode("utf-8"))
            self.logger.error(message)
            raise CommandException(message)
