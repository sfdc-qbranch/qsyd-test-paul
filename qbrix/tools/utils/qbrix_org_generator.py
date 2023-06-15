from genericpath import isfile
import json
import os
import re
import sys
import subprocess
import time
import shutil
import random
from abc import abstractmethod
from time import sleep

import yaml
from cumulusci.core.config import ScratchOrgConfig
from cumulusci.tasks.sfdx import SFDXBaseTask
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.exceptions import CommandException
from cumulusci.core.keychain import BaseProjectKeychain

LOAD_COMMAND = "sfdx force:apex:execute "


class Spin(SFDXBaseTask):
    keychain_class = BaseProjectKeychain
    task_options = {
        "devhubuser": {
            "description": "Template Id from a TSO or keyword of LATEST",
            "required": True
        },
        "devhubconsumerkey": {
            "description": "Consumerkey to test JWT authentication",
            "required": False
        },
        "mode": {
            "description": "type of spin needed. SCRATCH or TEMPLATE",
            "required": False
        },
        "scratch_config": {
            "description": "path to config json the contains the properties for the scratch org setup",
            "required": False
        },
        "devhubjwtkeyfile": {
            "description": "The on disk jwt private key for JWT authentication",
            "required": False
        },
        "githubpat": {
            "description": "GitHub Personal Access Token to be used to pulldown qbrix repos.",
            "required": False
        },
        "templateid": {
            "description": "Template Id from a TSO or keyword of LATEST",
            "required": False
        },
        "instance": {
            "description": "The instance to load the template onto",
            "required": False
        },
        "cciorg": {
            "description": "Once the org is spun up, import the org via cci org import to the aT",
            "required": False
        },
        "subdomain": {
            "description": "The directly supplied subdomain",
            "required": False,
            "default": "qbrix"
        },
        "signupemail": {
            "description": "The signup user email. If not provided, will fall back to the email associated to the dev hub user.",
            "required": False
        },
        "surpresssignupemail": {
            "description": "Template Id from a TSO or keyword of LATEST",
            "required": False,
            "default": True
        },
        "country": {
            "description": "Country code to place the org.",
            "required": False,
            "default": "US"
        },
        "language": {
            "description": "Language code for the org",
            "required": False,
            "default": "en"
        },
        "spinlength": {
            "description": "Number of days < 365 to apply to the spin. If the template source TSO is < than the amount, that will be applied.",
            "required": False,
            "default": 7
        },
        "runqbrixpostspin": {
            "description": "Template Id from a TSO or keyword of LATEST",
            "required": False
        },
        "applydefaultpassword": {
            "description": "Template Id from a TSO or keyword of LATEST",
            "required": False,
            "default": 7
        },
        "retryonerrorcodes": {
            "description": "Template Id from a TSO or keyword of LATEST",
            "required": False,
            "default": "C-99999"
        },
        "retrycount": {
            "description": "Template Id from a TSO or keyword of LATEST",
            "required": False,
            "default": 1
        },
        "maxwait": {
            "description": "Template Id from a TSO or keyword of LATEST",
            "required": False,
            "default": 60
        },
        "org": {
            "description": "Value to replace every instance of the find value in the source file.",
            "required": False
        },
        "company": {
            "description": "Company to be associated with the signup request. Default will be Salesforce",
            "required": False
        },
        "signuprequestid": {
            "description": "Existing signup request id that was submitted to monitor and hook.",
            "required": False
        },
        "deployqbrix": {
            "description": "Pipe delimited string of QBrix names to deploy once the org is stood up.",
            "required": False
        }
    }

    def _setprojectdefaults(self, instanceurl):
        subprocess.run([f"sfdx config:set instanceUrl={instanceurl}"], shell=True, capture_output=True)

    def _init_options(self, kwargs):
        super(Spin, self)._init_options(kwargs)
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
        if hasattr(self, 'keychain') == True and not self.keychain is None:
            return

        keychain_key = self.keychain_key if self.keychain_cls.encrypted else None

        if self.project_config is None:
            self.keychain = self.keychain_cls(self.universal_config, keychain_key)
        else:
            self.keychain = self.keychain_cls(self.project_config, keychain_key)
            self.project_config.keychain = self.keychain

    def _prepruntime(self):
        if hasattr(self, 'keychain') == False or self.keychain is None:
            self._load_keychain()

        # if not passed in - fall back to the key ring data
        if "mode" not in self.options:
            self.mode = "SCRATCH"
        else:
            self.mode = self.options["mode"]

        if "scratch_config" not in self.options:
            self.scratch_config = "orgs/dev.json"
        else:
            self.scratch_config = self.options["scratch_config"]

        if "devhubuser" not in self.options:
            self.devhubuser = ""
        else:
            self.devhubuser = self.options["devhubuser"]

        if "templateid" not in self.options:
            self.templateid = "LATEST"
            self.resolvedtemplateid = None
        else:
            self.templateid = self.options["templateid"]
            self.resolvedtemplateid = self.options["templateid"]

        if "instance" not in self.options:
            self.instance = ""
        else:
            self.instance = self.options["instance"]

        if "cciorg" not in self.options:
            self.cciorg = "qbrix_dev"
        else:
            self.cciorg = self.options["cciorg"]

        if "subdomain" not in self.options:
            t = time.time()
            ml = int(t * 1000)
            self.subdomain = f"qbrix-{ml}"

        else:
            self.subdomain = self.options["subdomain"]

        if "spinusername" not in self.options:
            t = time.time()
            ml = int(t * 1000)
            self.spinusername = f"demo.eng@.{ml}.qbrix"
        else:
            self.spinusername = self.options["spinusername"]

        if "maxwait" not in self.options:
            self.maxwait = 60
        else:
            self.maxwait = int(self.options["maxwait"])

        if "retrycount" not in self.options:
            self.retrycount = 1
        else:
            self.retrycount = int(self.options["retrycount"])

        if "retryonerrorcodes" not in self.options or self.options["retryonerrorcodes"] is None or self.options[
            "retryonerrorcodes"] == "":
            self.retryonerrorcodes = []
        else:
            self.retryonerrorcodes = self.options["retryonerrorcodes"].split('|')

        if "spinlength" not in self.options:
            self.spinlength = 7
        else:
            self.spinlength = int(self.options["spinlength"])

        if "language" not in self.options:
            self.language = "en"
        else:
            self.language = self.options["language"]

        if "country" not in self.options:
            self.country = "US"
        else:
            self.country = self.options["country"]

        if "signupemail" not in self.options:
            self.signupemail = "qbrix-signuprequest@salesforce.com"
        else:
            self.signupemail = self.options["signupemail"]

        if "surpresssignupemail" not in self.options:
            self.surpresssignupemail = True
        else:
            self.surpresssignupemail = bool(self.options["surpresssignupemail"])

        if "company" not in self.options:
            self.company = "Salesforce"
        else:
            self.company = self.options["company"]

        if "signuprequestid" not in self.options:
            self.signuprequestid = None
        else:
            if (self.options["signuprequestid"] != ""):
                self.signuprequestid = self.options["signuprequestid"]
            else:
                self.signuprequestid = None

        if "devhubconsumerkey" not in self.options:
            if not os.getenv("DEVHUBCONSUMERKEY", None) is None:
                self.devhubconsumerkey = os.getenv("DEVHUBCONSUMERKEY", None)
            else:
                self.devhubconsumerkey = None
        else:
            self.devhubconsumerkey = self.options["devhubconsumerkey"]

        if "devhubjwtkeyfile" not in self.options:
            if not os.getenv("DEVHUBJWTKEYFILE", None) is None:
                self.devhubjwtkeyfile = os.getenv("DEVHUBJWTKEYFILE", None)
            else:
                self.devhubjwtkeyfile = None
        else:
            self.devhubjwtkeyfile = self.options["devhubjwtkeyfile"]

        if "qbrixowner" not in self.options:
            self.qbrixowner = "sfdc-qbranch"
        else:
            if (self.options["qbrixowner"] != ""):
                self.qbrixowner = self.options["qbrixowner"]
            else:
                self.qbrixowner = "sfdc-qbranch"

        if "githubpat" not in self.options:
            if not os.getenv("GITHUB_PAT", None) is None:
                self.githubpat = os.getenv("GITHUB_PAT", None)
            else:
                self.githubpat = None
        else:
            self.githubpat = self.options["githubpat"]


        if "deployqbrix" in self.options:
            if self.options["deployqbrix"] is None or self.options["deployqbrix"] == "":
                self.deployqbrix = []
            else:
                self.deployqbrix = self.options["deployqbrix"].split('|')
        else:
            self.deployqbrix = []
            try:
                with open('cumulusci.yml', 'r') as f:
                    data = yaml.safe_load(f)

                required_qbrix = data.get('project', {}).get('custom', {}).get('required_qbrix', [])

                if len(required_qbrix) > 0:
                    self.deployqbrix.extend(required_qbrix)
                else:
                    self.deployqbrix = []
                    
                self.logger.info(self.deployqbrix )
            except:
                self.deployqbrix = []
                self.logger.error('No Default Required QBrix Defined YML')

    def _createworkingarea(self):
        if os.path.isdir('.qbrix') == False:
            os.mkdir('.qbrix')

        subprocess.run([f"sfdx force:project:create --projectname {self.devhubuser} --json"], shell=True,
            capture_output=True, cwd=".qbrix")
        subprocess.run([f"sfdx force:config:set defaultusername={self.devhubuser} --json"], shell=True,
            capture_output=True,
            cwd=os.path.join('.qbrix', self.devhubuser))

    def _getlatesttemplate(self):
        self._createworkingarea()
        result = subprocess.run([
            f"sfdx force:data:soql:query -u {self.devhubuser} -q \"SELECT ID FROM TrialTemplate Order By CreatedDate DESC LIMIT 1\" --json"],
            shell=True, capture_output=True, cwd=os.path.join('.qbrix', self.devhubuser))

        if result is None: return None

        jsonresult = json.loads(result.stdout)

        if jsonresult["result"]["totalSize"] == 1:
            # trim to 15 because signup requests only accept 15 bytes - irony
            self.resolvedtemplateid = jsonresult["result"]["records"][0]["Id"][:15]

        # fallback
        return None

    def _getrequestedqbrixfordeploy(self):
        if self.deployqbrix is not None:
            for (x) in self.deployqbrix:
                if os.path.isdir(os.path.join(".qbrix", x)):
                    self.logger.info(f"qrbix {x} exists. Clearing cache to pull latest")
                    shutil.rmtree(os.path.join(".qbrix", x), ignore_errors=True)

                cmd = f"git clone https://{self.githubpat}:x-oauth-basic@github.com/{self.qbrixowner}/{x}"
                result = subprocess.run([f"{cmd}"], shell=True, capture_output=True, cwd=".qbrix")

                print(result.stdout)

    def _deployqbrix(self):
        for (x) in self.deployqbrix:
            targetdir = os.path.join(".qbrix", x)

            if os.path.isdir(targetdir):
                if self.mode == "TEMPLATE":
                    cmd = f"cci org import {self.spinusername} {self.cciorg}"
                else:
                    cmd = f"cci org import {self.cciorg} {self.cciorg}"

                result = subprocess.run([f"{cmd}"], shell=True, capture_output=True, cwd=targetdir)
                stdoutres = result.stdout.splitlines()
                [self.logger.info(i) for i in stdoutres]

                cmd = f"cci flow run deploy_qbrix --org {self.cciorg}"
                self.logger.info(f"Running qbix: {cmd} againsts {targetdir}")

                with subprocess.Popen(['cci', 'flow', 'run', 'deploy_qbrix', '--org', self.cciorg],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1,
                        universal_newlines=True, cwd=targetdir) as p:
                    for line in p.stdout:
                        self.logger.info(line[20:])  # process line here

                if p.returncode != 0:
                    raise subprocess.CalledProcessError(p.returncode, f"Failure running QBrix {x}")

            else:
                self.logger.error(f"{targetdir} is not found")

    def _submittemplate(self):
        if self.templateid == "LATEST":
            self._getlatesttemplate()

        self.signuprequestid = None
        result = subprocess.run([
            f"sfdx force:data:record:create -u {self.devhubuser} -s SignupRequest -v \"{self._buildsignupcommand()}\" --json"],
            shell=True, capture_output=True, cwd=os.path.join('.qbrix', self.devhubuser))

        if result is None: return

        jsonresult = json.loads(result.stdout)
        self.logger.info(jsonresult)

        self.signuprequestid = jsonresult["result"]["id"]
        sleep(10)
        self.logger.info(f"Signup Request Id: {self.signuprequestid}")

    def _submitscratchorg(self, retrycount=0):
        result = subprocess.run([
            f"{self._buildscratchorgcommand()}"],
            shell=True, capture_output=True, cwd=os.path.join('.qbrix', self.devhubuser))

        print(result.stdout)

        jsonresult = json.loads(result.stdout)

        self.logger.info(jsonresult)

        if (jsonresult["status"] != 0
                and jsonresult["result"]["name"] == 'REQUEST_LIMIT_EXCEEDED'
                and retrycount < 3):
            # REQUEST_LIMIT_EXCEEDED - pause a few seconds to give api limits a breather
            sleep(15)
            retrycount += 1
            self._submitscratchorg(retrycount=retrycount)

        if (jsonresult["status"] != 0):
            raise CommandException("Scratch Org Create Failed.")

        if (jsonresult["status"] == 0):
            self.spinusername = jsonresult["result"]["username"]

    def _buildsignupcommand(self):
        cmd = f"trialdays={self.spinlength} company={self.company} lastname=Eng firstname=Demo username={self.spinusername} subdomain={self.subdomain} country={self.country} templateId={self.resolvedtemplateid}"

        if not self.instance is None:
            cmd = f"{cmd} instance={self.instance}"

        if not self.signupemail is None:
            cmd = f"{cmd} signupemail={self.signupemail}"

        if not self.surpresssignupemail is None:
            cmd = f"{cmd} IsSignupEmailSuppressed={self.surpresssignupemail}"

        self.logger.info(cmd)

        return cmd

    def _buildscratchorgcommand(self):
        cmd = f"sfdx force:org:create --json  -f {self.scratch_config} -w 120 --targetdevhubusername {self.devhubuser} -n --durationdays {self.spinlength} --setalias {self.cciorg}  "

        self.logger.info(cmd)

        return cmd

    def _generateusername(self):
        t = time.time()
        ml = int(t * 1000)
        self.spinusername = f"demo.eng@.{ml}.qbrix"

    def _generatesubdomain(self):
        if (self.subdomain is None):
            t = time.time()
            ml = int(t * 1000)
            self.subdomain = f"qbrix-{ml}"

        return self.subdomain

    def _monitorrequest(self):
        maxwait = self.maxwait
        if hasattr(self, "signuprequestid"):
            while not self._checktempaltestatuscomplete():
                sleep(60)
                maxwait = maxwait - 1

                if maxwait == 0:
                    raise CommandException("Max Wait Time Met")
                else:
                    self.logger.info(f"Polling in 60 seconds...{maxwait} wait cycles remain")

        else:
            raise CommandException("No signup request id found.")

    def _checktempaltestatuscomplete(self):
        if self.signuprequestid is not None:
            result = subprocess.run([
                f"sfdx force:data:record:get -u {self.devhubuser} -s SignupRequest -i \"{self.signuprequestid}\" --json"],
                shell=True, capture_output=True, cwd=os.path.join('.qbrix', self.devhubuser))

        if result is None:
            CommandException("Signup Request Id not found.")
        jsonresult = json.loads(result.stdout)

        self.logger.info(jsonresult)

        if jsonresult["status"] == 0:
            if jsonresult["result"]["Status"] == "Error":
                errorcode = jsonresult["result"]["ErrorCode"]
                if errorcode in self.retryonerrorcodes and self.retrycount > 0:
                    self.logger.error(f"The template spin failed for error code: {errorcode}. Attempting retry.")
                    self._submittemplate(self)
                    self.retrycount = self.retrycount - 1
                else:
                    raise CommandException(f"The template has failed for error code: {errorcode}")

            if jsonresult["result"]["Status"] == "InProgress" or jsonresult["result"]["Status"] == "New":
                self.logger.info("Spin still In Progress.")

                return False

            if jsonresult["result"]["Status"] == "Success":
                if self.devhubconsumerkey is not None and self.devhubjwtkeyfile is not None:
                    self.logger.info("Spin Successful. Waiting to verify JWT connectivity...")
                    sleep(600)  # force pause for 10 minutes to give SF core time to do the voodoo needed
                    self.spinusername = jsonresult["result"]["Username"]
                    self._forcelogout(self.spinusername)
                    spinjwtresult = self._connectspinviajwt(jsonresult["result"]["Username"])
                    maxjwt = 10
                    while spinjwtresult["status"] == 1:
                        spinjwtresult = self._connectspinviajwt(jsonresult["result"]["Username"])
                        maxjwt = maxjwt - 1
                        sleep(90)
                        self.logger.info("Waiting to connect JWT...")
                        if (maxjwt == 0):
                            raise CommandException(
                                "Unable to establish JWT authentication to template spin within poll time")

                    self.logger.info(spinjwtresult)
                    self.jwtresult = spinjwtresult
                    if spinjwtresult is not None:
                        if self.cciorg is None:
                            # we are done
                            return True
                        else:
                            # import the org post JWT auth into the target CCI org env.
                            if self.cciorg is not None:
                                self._importspinusertocciorg(jsonresult["result"]["Username"])
                    else:
                        raise CommandException("Unable to establish JWT authentication to template spin.")

                return True

        return False

    def _forcelogout(self, signupusername: str):
        try:
            cmd = f"sfdx auth:logout -p -u {signupusername}"
            subprocess.run([f"{cmd}"], shell=True, capture_output=True)
        except Exception as e:
            self.logger.error(e)

    def _connectspinviajwt(self, signupusername: str):
        cmd = f"sfdx auth:jwt:grant --username {signupusername} --jwtkeyfile {self.devhubjwtkeyfile} --clientid \"{self.devhubconsumerkey}\" --json"
        self.logger.info(cmd)

        if (not self.cciorg is None):
            cmd = f"{cmd} --setalias {self.cciorg}"

        result = subprocess.run([f"{cmd}"], shell=True, capture_output=True)
        jsonresult = json.loads(result.stdout)
        self.logger.info(jsonresult)
        return jsonresult

    def _importspinusertocciorg(self, signupusername: str):
        if self.cciorg is None:
            raise CommandException("Target CCI Org has not been set and cannot import a spin username.")

        result = subprocess.run([f"cci org import {signupusername} {self.cciorg}"], shell=True, capture_output=True)
        self.logger.info(result.stdout)

    def _run_task(self):
        self._prepruntime()

        # we may need to pre pull qbrix down to for pre-deploy
        self._getrequestedqbrixfordeploy()

        # setups Hub Access for scratch or template or template lookup
        self._createworkingarea()

        if self.mode == "TEMPLATE":
            if self.signuprequestid is None:
                # from 5 to 90 we will random pause to create some delay
                randomwaith = random.randrange(5, 90, 1)
                sleep(randomwaith)
                self._submittemplate()

            self._monitorrequest()
        else:
            # we are in scratch org mode
            if self.scratch_config is None:
                raise CommandException("Scratch org config not set.")

            self._submitscratchorg()

        self.logger.info(self.cciorg)
        self.logger.info(self.mode)
        self.logger.info(self.spinusername)

        self._importspinusertocciorg(self.spinusername)

        # deploy any qbrixs prior
        self._deployqbrix()

    def _handle_returncode(self, returncode, stderr):
        if returncode:
            message = "Return code: {}".format(returncode)
            if stderr:
                message += "\nstderr: {}".format(stderr.read().decode("utf-8"))
            self.logger.error(message)
            raise CommandException(message)
