from genericpath import isfile
from time import sleep
import requests
import json
import os
import re
import sys
import subprocess
import base64
from abc import abstractmethod

from cumulusci.core.config import ScratchOrgConfig
from cumulusci.tasks.sfdx import SFDXBaseTask
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.exceptions import CommandException
from cumulusci.core.keychain import BaseProjectKeychain

LOAD_COMMAND = "sfdx force:apex:execute "

#TODO: MOVE OUT OT Industries BaseConfig
class SFIDirectDatapackDeployer(SFDXBaseTask):
    
    keychain_class = BaseProjectKeychain
    task_options = {
        "org": {
            "description": "Value to replace every instance of the find value in the source file.",
            "required": False
        },
        "datapacks": {
            "description": "1 or more paths to the vlocity datapack json file exported via the Org UI. VBT exports are not supported.",
            "required": False
        }
    }
    
    def _setprojectdefaults(self, instanceurl):
        subprocess.run([f"sfdx config:set instanceUrl={instanceurl}"], shell=True, capture_output=True)

    def _init_options(self, kwargs):
        super(SFIDirectDatapackDeployer, self)._init_options(kwargs)
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

        if not self.org_config.access_token is None:
            self.accesstoken = self.org_config.access_token

        if not self.org_config.instance_url is None:
            self.instanceurl = self.org_config.instance_url
            
        if "datapacks" in self.options and not self.options["datapacks"] is None:
            self.datapacks = self.options["datapacks"]
        else:
            self.datapacks = []
            self.logger.info("No Datapacks Specified")
            
    def deploy_datapacks(self):
        for datapackfile in self.datapacks:
            self.logger.info(f"DataPack::{datapackfile}")
            if os.path.isfile(datapackfile):
                
                targetnamespace = self.determinenamespace(self.accesstoken)
                self.logger.info(f"TargetNamespace::{targetnamespace}")

                with open(datapackfile, "r") as tmpFile:
                    datapackcontents = tmpFile.read()
                    tmpFile.close()
                datapackcontents = datapackcontents.replace("%vlocity_namespace%",targetnamespace)
                
                dpdict={
                    "VlocityDataPackData": json.loads(datapackcontents),
                    "ignoreAllErrors": True
                }
                
                dppayload =base64.b64encode(json.dumps(dpdict).encode("utf-8"))
                
                
                dictpayload= {
                    "payload": str(dppayload.decode()),
                    "dpStep": "",
                    "status": ""
                    }
                self.process_datapack_payload(json.dumps(dictpayload))
                
            else:
                self.logger.error(f"DataPack::{datapackfile}::File Not Found")
                
    def process_datapack_payload(self,payload:str):
        if(payload is None):
            return
        targeturl =f"{self.org_config.instance_url}/services/apexrest/SFIDirectDatapackAPI"
        try:
            url = targeturl
            headers = {
            'Authorization': f'Bearer {self.accesstoken}',
            'Content-Type': 'application/json'
            }

            #self.logger.info(f"Payload::{payload}")
            response = requests.request("POST", url, headers=headers, data=payload)            
            payloadresponse = json.loads(response.text)
            
            status =payloadresponse["status"]
            msg=f"DataPack Processing::Status::{status}"
            self.logger.info(msg)
            
        
            # we will auto activate till we get a staus of error or dpStep and Status of complete Complete
            #yes dpStep complete is lower case
            if payloadresponse["status"] == "Error" or (payloadresponse["dpStep"] == "complete" and payloadresponse["status"] == "Complete"):
                status =payloadresponse["status"]
                msg=f"DataPack Processing Finished::Status::{status}"
                #we either ran into an error or went all the way to activate complete
                self.logger.info(msg)
                return None
            else:
                #echo it back through
                sleep(2)
                return  self.process_datapack_payload(response.text)
            
            


        except BaseException as err:
            self.logger.error(f"Datapack Deploy Error::{err}")
        

    def _setprojectdefaults(self, instanceurl):
        subprocess.run([f"sfdx config:set instanceUrl={instanceurl}"], shell=True, capture_output=True)
        
    def determinenamespace(self, username: str):

        result = subprocess.run([
            f"sfdx force:data:soql:query -u {username} -q \"SELECT NamespacePrefix FROM PackageLicense where NamespacePrefix in ('omnistudio','vlocity_cmt','vlocity_ps','vlocity_ins') LIMIT 1\" --json"],
            shell=True, capture_output=True)

        self.logger.info(result.stdout)
        if result is None: return "omnistudio"

        jsonresult = json.loads(result.stdout)

        if jsonresult["result"]["totalSize"] == 1:
            return jsonresult["result"]["records"][0]["NamespacePrefix"]

        # fallback
        return "omnistudio"
        
    def _run_task(self):
        self._prepruntime()
        self._setprojectdefaults(self.instanceurl)
        self.deploy_datapacks()
        
