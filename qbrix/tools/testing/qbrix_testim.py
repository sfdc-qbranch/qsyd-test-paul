import json
import os
import uuid
from abc import abstractmethod

from cumulusci.core.exceptions import CommandException
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.tasks.command import Command

# testim --token "$TESTIM_KEY" --project "$TESTIM_PROJECT" --grid "Testim-Grid" --suite "$SUITE_NAME" --base-url $LOGIN_URL
RUN_CMD = "testim --token '{testimtoken}' --project '{testimproject}' --grid '{testimgrid}' --name '{testimname}' --base-url '{baseurl}'"


class RunTestim(Command):
    keychain_class = BaseProjectKeychain

    task_docs = """
    Runs a given Testim script against a Salesforce org.
    """

    task_options = {
        "testimtoken": {
            "description": "Access Token to the Testim services. If not supplied will default to the Env Variable: TESTIM_KEY",
            "required": False
        },
        "testimproject": {
            "description": "Testim project. If not supplied will default to the Env Variable: TESTIM_PROJECT",
            "required": False
        },
        "testimgrid": {
            "description": "Testim grid. If not supplied will default to Testim-Grid",
            "required": False
        },
        "testimname": {
            "description": "Testim test name.",
            "required": True
        },
        "accesstoken": {
            "description": "Passed in accesstoken associated to the targetusername and instance url.",
            "required": False
        },
        "parameters": {
            "description": "A dictionary of parameters.",
            "required": False
        },
        "parameterfile": {
            "description": "Relative path to the parameter file to be passed into the Testim test",
            "required": False
        },
        "org": {
            "description": "Value to replace every instance of the find value in the source file.",
            "required": False
        }
    }

    def _init_options(self, kwargs):
        super(RunTestim, self)._init_options(kwargs)
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

    def _prepruntime(self):

        if ("org" in self.options and not self.options["org"] is None) and self.keychain is None:
            self._load_keychain()
            self.logger.info("Org passed in but no keychain found in runtime")

        # testimproject
        if "testimproject" in self.options and self.options["testimproject"]:
            self.testimproject = self.options["testimproject"]
        else:
            self.testimproject = os.environ.get('TESTIM_PROJECT')

        # testimgrid
        if "testimgrid" in self.options and self.options["testimgrid"]:
            self.testimgrid = self.options["testimgrid"]
        else:
            self.testimgrid = "Testim-Grid"

        # testimname
        if "testimname" in self.options and self.options["testimname"]:
            self.testimname = self.options["testimname"]
        else:
            self.testimname = ""

        # testimtoken
        if "testimtoken" in self.options and self.options["testimtoken"]:
            self.testimtoken = self.options["testimtoken"]
        else:
            # fallback to environment variable
            self.testimtoken = os.environ.get('TESTIM_KEY')

        # parameter file
        if "parameterfile" in self.options and self.options["parameterfile"]:
            self.parameterfile = self.options["parameterfile"]
        else:
            self.parameterfile = ""

        # if not passed in - fall back to the key ring data
        if "accesstoken" in self.options and self.options["accesstoken"]:
            self.accesstoken = self.options["accesstoken"]
        else:
            self.accesstoken = self.org_config.access_token

        # if not passed in - fall back to the key ring data
        if "instanceurl" in self.options and self.options["instanceurl"]:
            self.instanceurl = self.options["instanceurl"]
        else:
            self.instanceurl = self.org_config.instance_url

        # default to collapse to false
        parameterscollapsevalues = False

        if "parameterscollapsevalues" in self.options and self.options["parameterscollapsevalues"]:
            parameterscollapsevalues = bool(self.options["parameterscollapsevalues"])

        self.baseurl = f"{self.instanceurl}/secur/frontdoor.jsp?sid={self.accesstoken}"

        if "parameters" in self.options and self.options["parameters"]:
            # cast to a dictionary
            parmsdic = self.options["parameters"]
            parmsfilename = f"{uuid.uuid4().hex}.json"
            parmsdata = json.dumps(parmsdic)  # default
            if parameterscollapsevalues:

                mainkey = list(parmsdic.keys())[0]
                result = []
                collapsekey = list(parmsdic.keys())[0]
                childdict = dict(parmsdic[collapsekey].items())

                for i, (k, v) in enumerate(childdict.items()):
                    result.append(v)

                parmsdata = json.dumps({mainkey: result})

            # since we are using a parameter set defined in the yml, we will generate a temp file and supply that as the parameterfile.
            with open(parmsfilename, "w") as tmpFile:
                tmpFile.write(parmsdata)
                tmpFile.close()

            self.parameterfile = parmsfilename

    def _run_task(self):

        self._prepruntime()
        cmd = self._get_command()

        self.options["command"] = cmd
        output = []
        self._run_command(
            command=self._get_command(),
            env=self.env,
            output_handler=output.append,
            return_code_handler=self._handle_returncode,
        )
        resp = output[0].decode("utf-8")

    def _get_command(self):
        command = RUN_CMD.format(

            testimtoken=self.testimtoken,
            testimproject=self.testimproject,
            testimgrid=self.testimgrid,
            testimname=self.testimname,
            baseurl=self.baseurl
        )

        if self.parameterfile != "":
            command += f" --params-file '{self.parameterfile}'"

        return command

    def _handle_returncode(self, returncode, stderr):
        if returncode:
            message = "Return code: {}".format(returncode)
            if stderr:
                message += "\nstderr: {}".format(stderr.read().decode("utf-8"))
            self.logger.error(message)
            raise CommandException(message)
