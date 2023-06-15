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

#This extension is really for running a CCI style flow in a single shell. This is to get around
#granular task behavior within Metadeploy
class Deploy(SFDXBaseTask):
    keychain_class = BaseProjectKeychain
    task_options = {
        
        "org": {
            "description": "cci org list identifier",
            "required": False
        },
        "entrypoint": {
            "description": "Entry point to run against the qbrix. Default is deploy_qbrix",
            "required": False
        },
        "entrypointtype": {
            "description": "Entry point type of task or flow. Default is flow",
            "required": False
        }
    }
    
    def _setprojectdefaults(self, instanceurl):
        subprocess.run([f"sfdx config:set instanceUrl={instanceurl}"], shell=True, capture_output=True)

    def _init_options(self, kwargs):
        super(Deploy, self)._init_options(kwargs)
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
        
        if ("org" in self.options and not self.options["org"] is None) and self.keychain is None:
            self._load_keychain()
            self.logger.info("Org passed in but no keychain found in runtime")
            
        print(self.options)
        
        if self.org_config.name is not None:
            self.cciorg = self.org_config.name
            self.logger.info(f'USING CCIORG {self.cciorg}')
        else:
            self.logger.info(f'DEFAULTING CCIORG')
            self.cciorg = "current_org"
        
        if "entrypoint" not in self.options:
            self.entrypoint = "deploy_qbrix"
        else:
            self.entrypoint = self.options["entrypoint"]
            
        if "entrypointtype" not in self.options:
            self.entrypointtype = "flow"
        else:
            self.entrypointtype = self.options["entrypointtype"]
            
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


    def _deployqbrix(self):
        
        #self.logger.info(f'ENTRYPOINT::{self.entrypoint}')
        #self.logger.info(f'ENTRYPOINTTYPE::{self.entrypointtype}')
        #self.logger.info(f'TARGETORG::{self.cciorg}')
        
        orglist=subprocess.run([f"cci org list"], shell=True, capture_output=True)
        #self.logger.info(orglist)
        srvclist=subprocess.run([f"cci service list"], shell=True, capture_output=True)
        #self.logger.info(srvclist)
        srvclist=subprocess.run([f"cci org info {self.cciorg}"], shell=True, capture_output=True)
        #self.logger.info(srvclist)
        
        hashedalias = "cciorg"+str(hash(self.accesstoken))
        #self.logger.info(hashedalias)
        
        sfdximport=subprocess.run([f"export SFDX_ACCESS_TOKEN='{self.accesstoken}' && sfdx force:auth:accesstoken:store --instanceurl {self.instanceurl} -a {hashedalias} --noprompt --json --loglevel DEBUG "], shell=True, capture_output=True)
        #self.logger.info(sfdximport)
        
        sfdximport=subprocess.run([f"cci org import {hashedalias} {hashedalias}"], shell=True, capture_output=True)
        #self.logger.info(sfdximport)
        
        orglist=subprocess.run([f"cci org list"], shell=True, capture_output=True)
        #self.logger.info(orglist)
        
    
        with subprocess.Popen(['cci', self.entrypointtype, 'run', self.entrypoint, '--org', hashedalias],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1,
                universal_newlines=True) as p:
            for line in p.stdout:
                self.logger.info(line[20:])  # process line here
                
            for line in p.stderr:
                self.logger.error(line[20:])  # process line here

        if p.returncode != 0:
            raise subprocess.CalledProcessError(p.returncode, f"Failure running QBrix {self.entrypointtype} {self.entrypoint} ")
        
        
    def _run_task(self):
        self._prepruntime()
        self._deployqbrix()
