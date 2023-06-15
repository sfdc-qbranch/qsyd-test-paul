from genericpath import isfile
import json
import requests
import os
import re
import sys
import subprocess
import time
import shutil
import random
from abc import abstractmethod
from time import sleep
import atexit
import uuid
import socket
from datetime import datetime



from cumulusci.core.config import ScratchOrgConfig
from cumulusci.tasks.sfdx import SFDXBaseTask
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.exceptions import CommandException
from cumulusci.core.keychain import BaseProjectKeychain

LOAD_COMMAND = "sfdx force:apex:execute "

class InstallRecorder(SFDXBaseTask):
    
    
    task_options = {
            "org": {
                "description": "Target org instance installing the qbrix",
                "required": False
            }
            ,
            "context":{
                "description": "Additional context to add as part of the install record.",
                "required": False
            }
            ,
            "explicitexit":{
                "description": "When set to true, indicates tracking is flagged as done and telemetry should be sent",
                "required": False
            }
        }
     
    def _setprojectdefaults(self, instanceurl):
        subprocess.run([f"sfdx config:set instanceUrl={instanceurl}"], shell=True, capture_output=True)

    def _init_options(self, kwargs):
        super(SFDXBaseTask, self)._init_options(kwargs)
        
        try:
            self._trackingdata = None
            self.qbrixname = None
            self.context = None
            
            self._starttimestamp=datetime.utcnow()
            self._hooks = ExitHooks()
            self._hooks.hook()
            
            if(not self.org_config is None and self.org_config.tracking_data is None):
                self.org_config.tracking_data={}
                
            
            
            if(not self.org_config is None and self.org_config.genesis_qbrixname is None and not self.project_config.project__name is None):
                self.org_config.genesis_qbrixname=self.project_config.project__name
                self.logger.info(f"Setting Genesis QBrix::{self.org_config.genesis_qbrixname}")
                
            if(not self.org_config is None and self.org_config.qbrix_ambient_tracking_id is None):
                self.org_config.qbrix_ambient_tracking_id=str(uuid.uuid4())
                self.logger.info(f"Generated Ambient Transient Key::{self.org_config.qbrix_ambient_tracking_id}")
            else:
                self.logger.info(f"Existing Ambient Transient Key Found::{self.org_config.qbrix_ambient_tracking_id}")
                
            atexit.register(self._exithandler)
        except:
            print('No Tracking')
        

    @property
    def trackingdata(self):
        if(not self.org_config is None and self.org_config.tracking_data is None):
            self.org_config.tracking_data={}
            
        if(not self.project_config.project__name in self.org_config.tracking_data.keys()):
	        self.org_config.tracking_data[self.project_config.project__name] = {}

        return self.org_config.tracking_data[self.project_config.project__name]
    
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
            
        if ("qbrixname" in self.options and not self.options["qbrixname"] is None):
            self.qbrixname = self.options["qbrixname"]
            
        if ("explicitexit" in self.options and not self.options["explicitexit"] is None):
            self.trackingdata["explicitexit"] = bool(self.options["explicitexit"])
        else:
            #death is the exit
            self.trackingdata["explicitexit"] = False
            
        tmp=self.trackingdata["explicitexit"]
        self.logger.info(f"************explicitexit is {tmp}****************")
        
        if self.org_config.access_token is not None:
            self.accesstoken = self.org_config.access_token

        if self.org_config.instance_url is not None:
            self.instanceurl = self.org_config.instance_url

    def _run_task(self):
        
        self._prepruntime()
        self.run()
        

    def run(self):
        
        #if we are explicit done, we are 
        if(self.trackingdata["explicitexit"]):
            self.trackingdata["status"]="Completed"
            self.trackingdata["lasterror"]=""
            self.trackingdata["endtimestamp"]=(datetime.utcnow() - datetime(1970, 1, 1)).total_seconds()
            
            if("starttimestamp" in self.trackingdata.keys()):
                self.trackingdata["elapsedseconds"] =self.trackingdata["endtimestamp"] - self.trackingdata["starttimestamp"]
                
            self.__writertrackingtofile()
            self._recordtracking()
        
        else:
            
            
            self.trackingdata["genesis_qbrixname"]=self.org_config.genesis_qbrixname    
            self.trackingdata["ambient_tracking_id"]=self.org_config.qbrix_ambient_tracking_id
            self.trackingdata["qbrixname"]=self.project_config.project__name
            self.trackingdata["trackingid"]=str(uuid.uuid4())
            self.trackingdata["status"]='Started'
            self.trackingdata["username"]=self.org_config.username
            self.trackingdata["os"]=sys.platform
            self.trackingdata["qbrix_system_id"]=os.environ.get('QBRIX_SYSTEM_ID', 'UNKNOWN')
            self.trackingdata["instance"]=self.instanceurl
            self.trackingdata["hostname"]=socket.gethostname()
            self.trackingdata["starttimestamp"]=(datetime.utcnow() - datetime(1970, 1, 1)).total_seconds()
            
            orginzationdata = self._salesforce_query("select Id,CreatedDate,OrganizationType from Organization")
            if(not orginzationdata is None):
                self.trackingdata["orgid"] = orginzationdata["result"]["records"][0]["Id"]
                self.trackingdata["orgcreatedate"] = orginzationdata["result"]["records"][0]["CreatedDate"]
                self.trackingdata["organizationtype"] = orginzationdata["result"]["records"][0]["OrganizationType"]
            else:
                self.trackingdata["orgid"] = ""
                self.trackingdata["orgcreatedate"] = ""
                self.trackingdata["organizationtype"] = ""
            
            
            currentuserdata = self._salesforce_query(f"select Email from User where username='{self.org_config.username}'")
            if(not currentuserdata is None):
                self.trackingdata["installuseremail"] = currentuserdata["result"]["records"][0]["Email"]
            else:
                self.trackingdata["installuseremail"] = ""
                
            qlaborgdata = self._salesforce_query("select Identifier__c,Org_Type__c from QLabs__mdt")
            if(not qlaborgdata is None):
                self.trackingdata["qlabsorgidentifier"] = qlaborgdata["result"]["records"][0]["Identifier__c"]
                self.trackingdata["qlabsorgtype"] = qlaborgdata["result"]["records"][0]["Org_Type__c"]
            else:
                self.trackingdata["qlabsorgidentifier"] = ""
                self.trackingdata["qlabsorgtype"] = ""
            
                
            
            
            self.__writertrackingtofile()
        
       
            
        
        #Fake error
        #raise Exception("fake error for testing")
        

    def _salesforce_query(self,soql):
        
        if soql != "":

            dx_command = f"sfdx force:data:soql:query -q \"{soql}\" --json "
            subprocess.run(f"sfdx config:set instanceUrl={self.org_config.instance_url}", shell=True, capture_output=True)
            if isinstance(self.org_config, ScratchOrgConfig):
                dx_command += " -u {username}".format(username=self.org_config.username)
            else:
                dx_command += " -u {username}".format(username=self.org_config.access_token)

            result = subprocess.run(dx_command, shell=True, capture_output=True)
            subprocess.run("sfdx config:unset instanceUrl", shell=True, capture_output=True)
            
            if result.returncode > 0:

                if result.stderr:
                    error_detail = result.stderr.decode("UTF-8")
                    self.logger.error(f"Salesforce Query Error - Details: {error_detail}")
                else:
                    self.logger.error("Salesforce Query Failed, although no error detail was returned.")

                return None
                
            json_result = json.loads(result.stdout)
            self.logger.info(json_result)
            return json_result
        

        return None
 
 
    def _getlastccierror(self):
        try:
            result = subprocess.run("cci error info", shell=True, capture_output=True)
            if result.stderr:
                 return "Unable to access last CCI error info"
            else:
                return result.stdout.decode("UTF-8")
        except:
            return ""

    def __writertrackingtofile(self):
        if(self.project_config.project__name in self.trackingdata or self.trackingdata is None):
            self.logger.info("trackingdata is null")
            return
        
        try:
            if os.path.isfile(f".qbrix/installtracking_{self.project_config.project__name}.json"):
                os.remove(f".qbrix/installtracking_{self.project_config.project__name}.json")

            with open(f".qbrix/installtracking_{self.project_config.project__name}.json", "w+") as tmpFile:
                jsondata = json.dumps(self.trackingdata)
                tmpFile.write(jsondata)
                tmpFile.close()
            
        except:
            pass
       
        
    def _handle_returncode(self, returncode, stderr):
        if returncode:
            self.logger.error(message)
            self.trackingdata["status"]="Failed"
            self.__writertrackingtofile()
            message = "Return code: {}".format(returncode)
            if stderr:
                message += "\nstderr: {}".format(stderr.read().decode("utf-8"))
               
            raise CommandException(message)


    def _recordtracking(self):
        
        if(self.trackingdata is None):
            return
        
        url = "https://qbrix-core.herokuapp.com/qbrix/InstallTracking"
        payload = json.dumps(self.trackingdata )
        response = requests.request("POST", url, data=payload, verify=True)
        print(response.text)

     
    def _exithandler(self):
        
        if(self.trackingdata["explicitexit"]==False):
            
            self.logger.info('Exit Handler Entry')
            self.trackingdata["endtimestamp"]=(datetime.utcnow() - datetime(1970, 1, 1)).total_seconds()
            self.trackingdata["elapsedseconds"] =self.trackingdata["endtimestamp"] - self.trackingdata["starttimestamp"]

            if self._hooks.exit_code is not None:
                print("death by sys.exit(%d)" % self._hooks.exit_code)
                self.trackingdata["status"]="Failed"
                self.trackingdata["lasterror"]=self._getlastccierror()
                self.__writertrackingtofile()
                self._recordtracking()
                
            elif self._hooks.exception is not None:
                print("death by exception: %s" % self._hooks.exception)
                self.trackingdata["status"]="Failed"
                self.trackingdata["lasterror"]=self._getlastccierror()
                self.__writertrackingtofile()
                self._recordtracking()
                
            else:
                print("natural death")
                self.trackingdata["status"]="Completed"
                self.trackingdata["lasterror"]=""
                self.__writertrackingtofile()
                self._recordtracking()
                            
            self.logger.info('Exit Handler Exit')

        
class ExitHooks(object):
    def __init__(self):
        self.exit_code = None
        self.exception = None

    def hook(self):
        self._orig_exit = sys.exit
        self._orig_exc_handler = self.exc_handler
        sys.exit = self.exit
        sys.excepthook = self.exc_handler

    def exit(self, code=0):
        self.exit_code = code
        self._orig_exit(code)

    def exc_handler(self, exc_type, exc, *args):
        self.exception = exc
        self._orig_exc_handler(self, exc_type, exc, *args)

    