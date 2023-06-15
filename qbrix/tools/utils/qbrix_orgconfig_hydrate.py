import os
import json
import requests
import glob
import subprocess

from abc import abstractmethod
from cumulusci.core.config import ScratchOrgConfig
from cumulusci.tasks.sfdx import SFDXBaseTask
from cumulusci.core.exceptions import CommandException
from cumulusci.core.keychain import BaseProjectKeychain


class NGSFDXWrapper(SFDXBaseTask):
    task_options = {

        "org": {
            "description": "Value to replace every instance of the find value in the source file.",
            "required": False
        },
        "command": {
            "description": "SFDX Command to run",
            "required": False
        }
    }
    
    def _init_options(self, kwargs):
        super(NGSFDXWrapper, self)._init_options(kwargs)
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
        
        if "command" not in self.options or not self.options["command"]:
            self.command =None
        else:
            self.command =self.options["command"]
            
        if "targetusername" not in self.options or not self.options["targetusername"]:

            if not isinstance(self.org_config, ScratchOrgConfig):
                self.targetusername = self.org_config.access_token
            else:
                self.targetusername = self.org_config.username
        else:
            self.targetusername = self.options["targetusername"]
            
        
        subprocess.run(f"sfdx config:set instanceUrl={self.org_config.instance_url}", shell=True, capture_output=True)

        
        
        
    def _run_task(self):
        self._prepruntime()
        cmd = f"sfdx {self.command} --target-org '{self.targetusername}'"
        p= subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1,universal_newlines=True,shell=True)
        (out, err)=p.communicate()
        self.logger.info(out)
        self.logger.error(err)
        
        subprocess.run("sfdx config:unset instanceUrl", shell=True, capture_output=True)
        
        if p.returncode != 0:
            raise subprocess.CalledProcessError(p.returncode, f"SFDX Command Failed:: {cmd} ")
        
        
        

class NGBroom(SFDXBaseTask):
    task_options = {

        "sweep": {
            "description": "Filepath or glob pattern to sweep away.",
            "required": True
        },
        "recursive": {
            "description": "Run recursively",
            "required": False
        }
    }
    
    def _init_options(self, kwargs):
        super(NGBroom, self)._init_options(kwargs)
        
        
    def _prepruntime(self):

        
        if "sweep" not in self.options or not self.options["sweep"]:
            self.sweep =None
        else:
            self.sweep =self.options["sweep"]
        
        if "recursive" not in self.options or not self.options["recursive"]:
            self.recursive =True
        else:
            self.recursive =bool(self.options["recursive"])
        
    def _run_task(self):
        self._prepruntime()
        files = glob.glob(self.sweep,recursive=self.recursive)
        for filetosweep in files :
            if(os.path.isfile(filetosweep)):
                os.remove(filetosweep)
        
    
class NGAbort(SFDXBaseTask):
    task_options = {

        "message": {
            "description": "Message to capture when condition is found",
            "required": False
        }
    }
    
    def _init_options(self, kwargs):
        super(NGAbort, self)._init_options(kwargs)
        self.abortmessage=None
        
    def _prepruntime(self):

        # if not passed in - fall back to the key ring data
        if "message" not in self.options or not self.options["message"]:
            self.abortmessage ='The when codition was met'
        else:
            self.abortmessage =self.options["message"]
        
    def _run_task(self):
        self._prepruntime()
        raise Exception(f'This QBrix was stopped due to :: {self.abortmessage}')
        
class NGOrgConfig(SFDXBaseTask):
    keychain_class = BaseProjectKeychain
    task_options = {

        "org": {
            "description": "Value to replace every instance of the find value in the source file.",
            "required": False
        }
    }

    task_docs = """
    Gathers additional information from the source org and adds/updates the org_config collection so that you can then use these throughout your flow steps to define where clauses for tasks.
    """

    def _init_options(self, kwargs):
        super(NGOrgConfig, self)._init_options(kwargs)
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

        self._inject_max_runtime()
        self._seed_initial_cache()

    def _inject_max_runtime(self):

        if self.org_config.qbrix_cache is None:
            self.org_config.qbrix_cache = {}

        if self.org_config.max_org_api_version is None:
            self.org_config.max_org_api_version = self._get_org_max_api_version

        if self.org_config.is_qbrix_installed is None:
            self.org_config.is_qbrix_installed = self._is_qbrix_installed
            
        if self.org_config.is_object_in_org is None:
            self.org_config.is_object_in_org = self._is_object_present_in_org
            
        if self.org_config.is_psl_in_org is None:
            self.org_config.is_psl_in_org = self._is_psl_present_in_org
            
        if self.org_config.is_ps_in_org is None:
            self.org_config.is_ps_in_org = self._is_ps_present_in_org
            
        if self.org_config.is_namespace_installed is None:
            self.org_config.is_namespace_installed = self._is_package_namespace_installed
            
        if self.org_config.is_package_installed is None:
            self.org_config.is_package_installed = self._is_package_installed

        if self.org_config.is_org_identifier is None:
            self.org_config.is_org_identifier = self._check_id_or_guid_in_org
            
        if self.org_config.is_psl_minimal_qty_available_in_org is None:
            self.org_config.is_psl_minimal_qty_available_in_org = self._is_psl_minimal_qty_available_in_org
            
        if self.org_config.is_bulk_check_psl_minimal_qty_available_in_org is None:
            self.org_config.is_bulk_check_psl_minimal_qty_available_in_org = self._is_bulk_check_psl_minimal_qty_available_in_org
        
        if self.org_config.qbrix_cache_get is None:
            self.org_config.qbrix_cache_get = self._cache_item_get
            
        if self.org_config.qbrix_cache_set is None:
            self.org_config.qbrix_cache_set = self._cache_item_set
            
        if self.org_config.is_data_present is None:
            self.org_config.is_data_present = self._is_data_present_in_org
            
        if self.org_config.is_file is None:
            self.org_config.is_file = self._is_file
        
        if self.org_config.is_dir is None:
            self.org_config.is_dir = os.path.isdir
            
        if self.org_config.is_file_glob is None:
            self.org_config.is_file_glob = self._is_glob_file_search
            
        if self.org_config.is_scratch_org is None:
            self.org_config.is_scratch_org = self._is_scratch_org
            
        

    def _seed_initial_cache(self):
        if(self.org_config.qbrix_cache is None):
            self.org_config.qbrix_cache={}
            
    def _cache_item_get(self,key):
        if(self.org_config.qbrix_cache is None):
            self.org_config.qbrix_cache={}
        
        return self.org_config.qbrix_cache.get(key)
            
    def _cache_item_set(self,key,val):
        if(self.org_config.qbrix_cache is None):
            self.org_config.qbrix_cache={}
        
        self.logger.info(f'Cache::{key}::{val}')
        self.org_config.qbrix_cache[key]=val
        
    def _is_scratch_org(self):
        return ".scratch." in self.instanceurl
    
    def _is_file(self,filetofind):
        return os.path.isfile(filetofind)
    
    def _is_glob_file_search(self,filetofind,runrecursive=True):
        foundfiles =glob.glob(filetofind, recursive=runrecursive)
        for file in foundfiles:
            print(file)
        return len(foundfiles) >0
        



    def _is_qbrix_installed(self, qbrixname):

        url = f"{self.instanceurl}/services/data/v56.0/query/?q=select+MasterLabel+from+xDO_Base_QBrix_Register__mdt+where+MasterLabel='{qbrixname}'"
        headers = {
            'Authorization': f'Bearer {self.accesstoken}',
            'Content-Type': 'application/json'
        }
        response = requests.request("GET", url, headers=headers)
        # print(response.text)
        data = json.loads(response.text)
        self.logger.info(data["totalSize"])
        return data["totalSize"] == 1
    
    def _is_package_namespace_installed(self, namespace):

        url = f"{self.instanceurl}/services/data/v56.0/query/?q=select+NamespacePrefix+from+PackageLicense+where+NamespacePrefix='{namespace}'"
        headers = {
            'Authorization': f'Bearer {self.accesstoken}',
            'Content-Type': 'application/json'
        }
        response = requests.request("GET", url, headers=headers)
        # print(response.text)
        data = json.loads(response.text)
        self.logger.info(data["totalSize"])
        return data["totalSize"] == 1
    
    def _is_package_installed(self, packagename):

        url = f"{self.instanceurl}/services/data/v56.0/tooling/query/?q=select+SubscriberPackage.Name+from+InstalledSubscriberPackage+order+by+SubscriberPackage.Name"
        headers = {
            'Authorization': f'Bearer {self.accesstoken}',
            'Content-Type': 'application/json'
        }
        response = requests.request("GET", url, headers=headers)
        # print(response.text)
        data = json.loads(response.text)
        for pkg in data['records']:
            if(pkg['SubscriberPackage']['Name']==packagename):
                return True
            #self.logger.info(pkg['SubscriberPackage']['Name'])
        
        return False
    
    
    def _is_object_present_in_org(self, targetobject):
        
        self.logger.info(f"_is_object_present_in_org::{targetobject}")
        if(targetobject is None):
            return False
        
        #SELECT  QualifiedApiName FROM EntityDefinition Where QualifiedApiName=

        url = f"{self.instanceurl}/services/data/v56.0/query/?q=select+QualifiedApiName+from+EntityDefinition+where+QualifiedApiName='{targetobject}' LIMIT 1"
        headers = {
            'Authorization': f'Bearer {self.accesstoken}',
            'Content-Type': 'application/json'
        }
        response = requests.request("GET", url, headers=headers)
        # print(response.text)
        data = json.loads(response.text)
        self.logger.info(data["totalSize"])
        return data["totalSize"] == 1
    
    
    def _is_data_present_in_org(self, targetobject, filter,tooling=False):
        default = lambda o: f"<<non-serializable: {type(o).__qualname__}>>"
        org_config_json= json.dumps(self.org_config, default=default)
        self.logger.info(f"{os.listdir('.') }")
        
        self.logger.info(f"_is_data_present_in_org::ttargetobject::{targetobject}::filter::{filter}")
        
        url=""
        querytarget="query"
        if(tooling):
            querytarget="tooling/query"
        
        
        if(not filter is None):
            url = f"{self.instanceurl}/services/data/v56.0/{querytarget}/?q=select+Id+from+{targetobject}+where+({filter})"
        else:
            url = f"{self.instanceurl}/services/data/v56.0/{querytarget}/?q=select+Id+from+{targetobject}"
            
        self.logger.info(f"url::{url}")
        
        headers = {
            'Authorization': f'Bearer {self.accesstoken}',
            'Content-Type': 'application/json'
        }
        response = requests.request("GET", url, headers=headers)
        
        data = json.loads(response.text)
        #self.logger.info(data)
        self.logger.info(data["totalSize"])
        return data["totalSize"] > 0
        
        
        #fail closed
        return False
    
    
    def _is_psl_present_in_org(self, psl):
        
        #e.g. 
        #SELECT  id,MasterLabel,DeveloperName from PermissionSetLicense where (Masterlabel='OmniStudioDesigner' or DeveloperName='OmniStudioDesigner')

        url = f"{self.instanceurl}/services/data/v56.0/query/?q=select+Id+from+PermissionSetLicense+where+(Masterlabel='{psl}'+or+DeveloperName='{psl}')+LIMIT+1"
        headers = {
            'Authorization': f'Bearer {self.accesstoken}',
            'Content-Type': 'application/json'
        }
        response = requests.request("GET", url, headers=headers)
        # print(response.text)
        data = json.loads(response.text)
        self.logger.info(data["totalSize"])
        return data["totalSize"] == 1
    
    
        
    def _is_psl_minimal_qty_available_in_org(self, psl, qty):
        
        #e.g. 
        #SELECT  id,MasterLabel,DeveloperName from PermissionSetLicense where (Masterlabel='OmniStudioDesigner' or DeveloperName='OmniStudioDesigner')
        #self.logger.info(psl)
        #self.logger.info(qty)
        #self.logger.info(type(qty))
        
        url = f"{self.instanceurl}/services/data/v56.0/query/?q=select+Id,TotalLicenses,UsedLicenses+from+PermissionSetLicense+where+(Masterlabel='{psl}'+or+DeveloperName='{psl}')+LIMIT+1"
        headers = {
            'Authorization': f'Bearer {self.accesstoken}',
            'Content-Type': 'application/json'
        }
        response = requests.request("GET", url, headers=headers)
        #self.logger.info(response.text)
        data = json.loads(response.text)
        #self.logger.info(data["totalSize"])
        if data["totalSize"] == 0:
            return False
        
        totalqty= data["records"][0]["TotalLicenses"]
        usedqty= data["records"][0]["UsedLicenses"]
        
        #self.logger.info((totalqty-usedqty)>= qty)
        return (totalqty-usedqty) >= qty
    
    def _is_bulk_check_psl_minimal_qty_available_in_org(self, srcfile):
        
        #self.logger.info(f'Source File::{srcfile}')
        try:
            
            #fail closed
            if(os.path.exists(srcfile)==False):
                self.logger.error(f'PSL Bulk Check Source File not found::{srcfile}')
                return False
            
            
            filehandle = open(srcfile,"r")
            filecontents = filehandle.read()
            
            #self.logger.info(f'Source File Contents::{filecontents}')
            
            #fail closed
            if(len(filecontents)==0):
                return False
            
            psldict = json.loads(filecontents)
            
            for p in psldict.keys():
                qty = psldict[p]
                res = self._is_psl_minimal_qty_available_in_org(p,qty)
                if(res==False):
                    self.logger.error(f'Minimal Qty for: {p} not met. Required:{qty}')
                    return False
            #hurray-you survived the hunger games. may the odds be in your favor
            return True
        except Exception as e:
            self.logger.error(f'Failure in bulk check. Failing closed. {e}')
            #fail closed
            return False
               
               
        #fail closed
        self.logger.error(f'Failing closed.')
        return False
        
    
    def _is_ps_present_in_org(self, ps):
        
        #e.g. 
        #SELECT  id,MasterLabel,DeveloperName from PermissionSet where (Name='OmniStudioDesigner' or Label='OmniStudioDesigner')

        url = f"{self.instanceurl}/services/data/v56.0/query/?q=select+Id+from+PermissionSet+where+(Name='{ps}'+or+Label='{ps}')+LIMIT+1"
        headers = {
            'Authorization': f'Bearer {self.accesstoken}',
            'Content-Type': 'application/json'
        }
        response = requests.request("GET", url, headers=headers)
        # print(response.text)
        data = json.loads(response.text)
        self.logger.info(data["totalSize"])
        return data["totalSize"] == 1
    
    
    
    def _check_id_or_guid_in_org(self, identifier):
    
        #fail closed sine the object or access to the object is not present
        try:
            return (self._check_org_id_exists(identifier) or self._check_org_guid_exists(identifier))
        except:
          self.logger.error("Lookup of org identifier or guid failed. failing closed.")
            
        #fail closed sine the object or access to the object is not present
        return False
    
    #custom metadata does not support OR 
    def _check_org_id_exists(self, identifier):
        
        try:
            #e.g. 
            #SDO or GUID
            url = f"{self.instanceurl}/services/data/v56.0/query/?q=select+Id+from+QLabs__mdt+where+(Org_Type__c='{identifier}')+LIMIT+1"
            headers = {
                'Authorization': f'Bearer {self.accesstoken}',
                'Content-Type': 'application/json'
            }
            response = requests.request("GET", url, headers=headers)
            # print(response.text)
            data = json.loads(response.text)
            self.logger.info(data["totalSize"])
            return data["totalSize"] == 1
        except:
            self.logger.error("Lookup of org identifier failed. failing closed.")
            
        #fail closed sine the object or access to the object is not present
        return False
    
     #custom metadata does not support OR 
    def _check_org_guid_exists(self, identifier):
        
        try:
            #e.g. 
            #SDO or GUID
            url = f"{self.instanceurl}/services/data/v56.0/query/?q=select+Id+from+QLabs__mdt+where+(Identifier__c='{identifier}')+LIMIT+1"
            headers = {
                'Authorization': f'Bearer {self.accesstoken}',
                'Content-Type': 'application/json'
            }
            response = requests.request("GET", url, headers=headers)
            # print(response.text)
            data = json.loads(response.text)
            self.logger.info(data["totalSize"])
            return data["totalSize"] == 1
        except:
            self.logger.error("Lookup of org guid failed. failing closed.")
            
        #fail closed sine the object or access to the object is not present
        return False
        


    def _get_org_max_api_version(self):

        url = f"{self.instanceurl}/services/data/"
        headers = {
            'Authorization': f'Bearer {self.accesstoken}',
            'Content-Type': 'application/json'
        }
        response = requests.request("GET", url, headers=headers)
        data = json.loads(response.text)
        
        return float(data[-1]['version'])

    def _run_task(self):

        self._prepruntime()

    def _handle_returncode(self, returncode, stderr):
        if returncode:
            message = "Return code: {}".format(returncode)
            if stderr:
                message += "\nstderr: {}".format(stderr.read().decode("utf-8"))
            self.logger.error(message)
            raise CommandException(message)

class NGCacheAdd(SFDXBaseTask):
    task_options = {

        "key": {
            "description": "Message to capture when condition is found",
            "required": False
        },
        "value": {
            "description": "Literal value or expression between ${{}} ",
            "required": False
        }
    }
    
    def _init_options(self, kwargs):
        super(NGCacheAdd, self)._init_options(kwargs)
        self.env = self._get_env()
        
        
    def _prepruntime(self):
        
        if "key" not in self.options or not self.options["key"]:
            raise Exception(f'No key provided to add to cache')
        else:
            self.key =self.options["key"]
            
        if "value" not in self.options or not self.options["value"]:
            raise Exception(f'No key provided to add to cache')
        else:
            self.value =self.options["value"]
        
    def _run_task(self):
        self._prepruntime()
        
        if(self.value.startswith("${{") and self.value.endswith("}}")):
            try:
                sub1="${{"
                sub2="}}"
                idx1 = self.value.find(sub1)
                idx2 = self.value.find(sub2)
                exp = self.value[idx1 + len(sub1) + 1: idx2]
                
                #exit if inline import detected
                if "__import__" in exp:
                    return
                
                compliledcode = compile(exp, "<string>", "eval")
                #no builtins = no __import__ # DO NOT allow globals
                #restrict scope to expression - no builtins and only locals self
                res = eval(compliledcode,{},{"self":self})
                #self.logger.info(f"EXPRESSION::VAL::{res}")
                self.org_config.qbrix_cache_set(self.key,res)
            except Exception as inst:
                self.logger.error(f"Unable to evaluate dynamic express::{inst}")
        else:
             ngorgconfig._cache_item_set(self.key,self.value)
        
        
    