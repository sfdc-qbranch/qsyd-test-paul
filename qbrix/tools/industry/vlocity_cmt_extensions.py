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

#this is very specific to Vlocity CMT setup    
class CMTDeployDefaultLayouts(SFDXBaseTask):
    keychain_class = BaseProjectKeychain
    task_options = {
        "org": {
            "description": "Value to replace every instance of the find value in the source file.",
            "required": False
        }
    }

    def _setprojectdefaults(self, instanceurl):
        subprocess.run([f"sfdx config:set instanceUrl={instanceurl}"], shell=True, capture_output=True)

    def _init_options(self, kwargs):
        super(CMTDeployDefaultLayouts, self)._init_options(kwargs)
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

    def deploy_default_layout(self):
        
        #env setup for sfdx 
        subprocess.run([f"sfdx config:set instanceUrl={self.instanceurl}"], shell=True, capture_output=True)
        
        MAX_CYCLES = 60
        
        deleteapex="qbrix_local/scripts/deletecmtdefaultlayouts.cls"
        initialRedeployApex="qbrix_local/scripts/initialcmtredeploydefualtlayouts.cls"
        pollRedeployApex="qbrix_local/scripts/pollcmtdatapackdeployqueue.cls"
        pollRedeployApexClassic="qbrix_local/scripts/pollcmtdatapackdeployqueueclassic.cls"
        
        #Run the intial delete
        deletecmd=f"sfdx force:apex:execute -f {deleteapex} -u {self.accesstoken} --json"
        resp = subprocess.run([deletecmd], shell=True, capture_output=True)
        self.logger.info("Delete Executed")
        #wait a minute - let jobs spin up server side
        sleep(60)
        
        #Run the intitial loadta - to seed the server side dp state
        initdeploycmd=f"sfdx force:apex:execute -f {initialRedeployApex} -u {self.accesstoken} --json"
        resp = subprocess.run([initdeploycmd], shell=True, capture_output=True)
        self.logger.info("Running Initial Load")
        sleep(60)
        
        cmd = f"sfdx force:data:soql:query -u {self.accesstoken} -q \"select id,ProcessStatus from OmniDataPack where Name='QBrixDeploy' and ProcessStatus in ('Ready') ORDER BY CREATEDDATE DESC LIMIT 1\" --json"
        isclassdatapackload=self._is_classic_datapack()
        
        if(isclassdatapackload):
            cmd = f"sfdx force:data:soql:query -u {self.accesstoken} -q \"select id,vlocity_cmt__Status__c from vlocity_cmt__VlocityDataPack__c where Name='QBrixDeploy' and vlocity_cmt__Status__c in ('Ready') ORDER BY CREATEDDATE DESC LIMIT 1\" --json"
            
        result = subprocess.run([cmd], shell=True, capture_output=True)

        if result is None:
            return None

        jsonresult = json.loads(result.stdout)
        self.logger.info(jsonresult)

        if jsonresult["result"]["totalSize"] == 1:
            
            queueid=jsonresult["result"]["records"][0]["Id"]
            
            if(isclassdatapackload):
                status = jsonresult["result"]["records"][0]["vlocity_cmt__Status__c"]
            else:
                status = jsonresult["result"]["records"][0]["ProcessStatus"]
            
            while((status=="Ready" or status=="InProgress") and (MAX_CYCLES>0)) :
                
                self.logger.info(f"Loading Status::{status}")
                
                if(isclassdatapackload):
                    pollcmd=f"sfdx force:apex:execute -f {pollRedeployApexClassic} -u {self.accesstoken} --json"
                else:
                    pollcmd=f"sfdx force:apex:execute -f {pollRedeployApex} -u {self.accesstoken} --json"
                
                
                subprocess.run([pollcmd], shell=True, capture_output=True)
    
    
                cmd = f"sfdx force:data:soql:query -u {self.accesstoken} -q \"select id,ProcessStatus from OmniDataPack where Name='QBrixDeploy' and Id='{queueid}' ORDER BY CREATEDDATE DESC LIMIT 1\" --json"
                
                if(isclassdatapackload):
                    cmd = f"sfdx force:data:soql:query -u {self.accesstoken} -q \"select id,vlocity_cmt__Status__c from vlocity_cmt__VlocityDataPack__c where Name='QBrixDeploy' and Id='{queueid}' ORDER BY CREATEDDATE DESC LIMIT 1\" --json"
                    
                result = subprocess.run([cmd], shell=True, capture_output=True)
                jsonresult = json.loads(result.stdout)
                
                if(isclassdatapackload):
                    status = jsonresult["result"]["records"][0]["vlocity_cmt__Status__c"]
                else:
                    status = jsonresult["result"]["records"][0]["ProcessStatus"]
                
                if(status =="Completed" or status =="Error"):
                    MAX_CYCLES = -1
                    break

                #decrement 
                MAX_CYCLES -= 1
                
                self.logger.info(f"Remaining Cycles::{MAX_CYCLES}")
                sleep(10)
                
    def _is_classic_datapack(self):
        
        cmd = f"sfdx force:data:soql:query -u {self.accesstoken} -q \"SELECT  QualifiedApiName FROM EntityDefinition Where QualifiedApiName= 'OmniDataPack'\" --json"
        result = subprocess.run([cmd], shell=True, capture_output=True)
        jsonresult = json.loads(result.stdout)
        #if it does not exist - we are in classic loading.
        return int(jsonresult["result"]["totalSize"]) ==0
        
                
    def _run_task(self):

        self._prepruntime(self)
        self._setprojectdefaults(self.instanceurl)
        self.deploy_default_layout()

    def _handle_returncode(self, returncode, stderr):
        if returncode:
            message = "Return code: {}".format(returncode)
            if stderr:
                message += "\nstderr: {}".format(stderr.read().decode("utf-8"))
            self.logger.error(message)
            raise CommandException(message)
