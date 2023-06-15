import json
import os
import subprocess
from abc import abstractmethod
from cumulusci.tasks.command import Command
from cumulusci.core.exceptions import CommandException
from cumulusci.core.keychain import BaseProjectKeychain


class FART(Command):
    keychain_class = BaseProjectKeychain

    task_docs = """
    Used to find and replace text within files in the project folder, typically pre-deployment. Replacement values can be specified or sourced from a target org using a SOQL statement.
    """

    task_options = {
        "srcfile": {
            "description": "Directory path to the export.json to upload",
            "required": True
        },
        "mode": {
            "description": "Run mode: Text or Between or SOQL or SOQL-Between",
            "required": False,
            "default": "Text"
        },
        "soql": {
            "description": "For run mode of SQOL, the soql statement to use in scalar mode to.",
            "required": False
        },
        "find": {
            "description": "Text pattern to locate in the source file.",
            "required": False
        },
        "findleft": {
            "description": "Left pattern string to locate in the text of the source file.",
            "required": False
        },
        "findright": {
            "description": "Right side of pattern to find in the text of the source file.",
            "required": False
        },
        "replacewith": {
            "description": "Value to replace every instance of the find value in the source file.",
            "required": False
        },
        "org": {
            "description": "Value to replace every instance of the find value in the source file.",
            "required": False
        },
        "format": {
            "description": "Format pattern to apply to the supplied replacewith or located value from a soql statement",
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

    def _prepruntime(self):

        if ("org" in self.options and not self.options["org"] is None) and self.keychain is None:
            self._load_keychain()
            self.logger.info("Org passed in but no keychain found in runtime")

        if "srcfile" not in self.options or not self.options["srcfile"]:
            raise ValueError('No source file provided to analyze.')
        else:
            self.fartpath = self.options["srcfile"]

        if "mode" not in self.options or not self.options["mode"]:
            self.fartmode = "Text"
        else:
            self.fartmode = self.options["mode"]

        # universal
        if "replacewith" not in self.options or not self.options["replacewith"]:
            self.fartreplacewith = None
        else:
            self.fartreplacewith = self.options["replacewith"]

        # universal
        if "find" not in self.options or not self.options["find"]:
            self.fartfind = None
        else:
            self.fartfind = self.options["find"]

        # format the replacewith value - we want {0}
        if "format" not in self.options or not self.options["format"]:
            self.formatval = None
        else:
            self.formatval = self.options["format"]
            if "{0}" not in self.formatval:
                self.formatval = None

        # universal
        if "tooling" not in self.options or not self.options["tooling"]:
            self.tooling = False
        else:
            self.tooling = bool(self.options["tooling"])

        if self.fartmode == "Between" or self.fartmode == "SOQL-Between":
            if "findleft" not in self.options or not self.options["findleft"]:
                self.fartfindleft = None
            else:
                self.fartfindleft = self.options["findleft"]

            if "findright" not in self.options or not self.options["findright"]:
                self.fartfindright = None
            else:
                self.fartfindright = self.options["findright"]

        if self.fartmode == "SOQL" or self.fartmode == "SOQL-Between":

            if "soql" not in self.options or not self.options["soql"]:
                self.soql = None
            else:
                self.soql = self.options["soql"]

            if self.org_config.access_token is not None:
                self.accesstoken = self.org_config.access_token

            if self.org_config.instance_url is not None:
                self.instanceurl = self.org_config.instance_url

    def run(self):
        if self.fartmode == "Text":
            self.runwithtext()
            
        if self.fartmode == "Cache":
            self.runwithcache()

        if self.fartmode == "Between":
            self.runtextbetween()

        if self.fartmode == "SOQL":
            self.runwithsoql()

        if self.fartmode == "SOQL-Between":
            self.runwithsoqlbetween()

    def runwithcache(self):
        cacheval = self.org_config.qbrix_cache_get(self.fartreplacewith)
        
        if(not cacheval is None):
            self.fart(self.fartpath, self.fartfind, cacheval, self.formatval)
        
    def runwithtext(self):
        self.fart(self.fartpath, self.fartfind, self.fartreplacewith, self.formatval)

    def runtextbetween(self):
        self.fartbetween(self.fartpath, self.fartfindleft, self.fartfindright, self.fartreplacewith, self.formatval)

    def runwithsoql(self):
        if self.soql is None or self.soql == "":
            return

        subprocess.run([f"sfdx config:set instanceUrl={self.instanceurl}"], shell=True, capture_output=True)

        self.fartsoql(self.fartpath, self.fartfind, self.accesstoken, self.soql, self.formatval, self.tooling)

    def runwithsoqlbetween(self):

        if self.soql is None or self.soql == "":
            return

        if self.fartfindleft is None or self.fartfindright is None:
            return

        subprocess.run([f"sfdx config:set instanceUrl={self.instanceurl}"], shell=True, capture_output=True)

        self.fartsoqlbetween(self.fartpath, self.fartfindleft, self.fartfindright, self.accesstoken, self.soql,
                             self.formatval, self.tooling)

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

    def fart(self, srcfile: str, find: str, replacewith: str, formatval: str):

        if os.path.isfile(srcfile):
            with open(f"{srcfile}", "r") as tmpFile:
                defcontents = tmpFile.read()
                tmpFile.close()

                #print(defcontents)

                # if defcontents.find(find) == -1:
                if formatval is None:
                    defcontentsmodified = defcontents.replace(find, replacewith)
                else:
                    defcontentsmodified = defcontents.replace(find, formatval.format(replacewith))

                with open(f"{srcfile}", "w") as tmpFile:
                    tmpFile.write(defcontentsmodified)
                    tmpFile.close()

        else:
            print("Provided Source File cannot be found:")

    def fartbetween(self, srcfile: str, left: str, right: str, replacewith: str, formatval: str):
        if os.path.isfile(srcfile):
            with open(f"{srcfile}", "r") as tmpFile:
                defcontents = tmpFile.read()
                tmpFile.close()

                if defcontents.index(left) == -1:
                    return

                startIndex = defcontents.index(left) + len(left)
                endIndex = defcontents.index(right, startIndex)
                if endIndex == -1:
                    return

                midContents = defcontents[startIndex:endIndex]

                if formatval is None:
                    defcontentsmodified = defcontents.replace(f"{left}{midContents}{right}",
                                                              f"{left}{replacewith}{right}")
                else:
                    defcontentsmodified = defcontents.replace(f"{left}{midContents}{right}",
                                                              f"{left}{formatval.format(replacewith)}{right}")

                with open(f"{srcfile}", "w") as tmpFile:
                    tmpFile.write(defcontentsmodified)
                    tmpFile.close()

    def getsoqldata(self, sfdxuser: str, soql: str, tooling: bool = False):
        if sfdxuser is None or soql is None:
            return None

        cmd = f"sfdx force:data:soql:query -u {sfdxuser} -q \"{soql}\" --json"

        if tooling:
            cmd = f"{cmd} -t"

        result = subprocess.run([cmd], shell=True, capture_output=True)

        if result is None:
            return None

        jsonresult = json.loads(result.stdout)

        if jsonresult["result"]["totalSize"] >= 1:
            print(jsonresult["result"]["records"][0][list(jsonresult["result"]["records"][0].keys())[1]])
            # we want the first key (1) after attributes(0). That is the first column and all we want
            return jsonresult["result"]["records"][0][list(jsonresult["result"]["records"][0].keys())[1]]

        # fallback
        return None

    def fartsoql(self, srcfile: str, find: str, sfdxaccesstoken: str, soql: str, formatval: str, tooling: bool = False):
        replacewith = self.getsoqldata(sfdxaccesstoken, soql, tooling)
        if replacewith is None:
            return
        self.fart(srcfile, find, replacewith, formatval)

    def fartsoqlbetween(self, srcfile: str, left: str, right: str, sfdxaccesstoken: str, soql: str, formatval: str,
                        tooling: bool = False):
        replacewith = self.getsoqldata(sfdxaccesstoken, soql, tooling)
        if replacewith is None:
            return
        self.fartbetween(srcfile, left, right, replacewith, formatval)
