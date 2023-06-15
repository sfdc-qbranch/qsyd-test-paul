import os
import re
import shutil
import subprocess
from abc import ABC


from cumulusci.core.tasks import BaseTask
from cumulusci.cli.runtime import CliRuntime
from qbrix.tools.shared.qbrix_console_utils import init_logger

log = init_logger()

class MetadataChecker(BaseTask, ABC):
    cci_cache_path = ".cci/projects"
    base_folders = set()
    
    task_docs = """
    MetadataChecker: this is a simple tool helps you finding if a metadata already exists in your source QBrix,
    This tool can work in two mode: Search mode and Scan mode
        To use search mode, run command like below:
            cci task run qbrix_metadata_checker --metadata_type the_type --api_names a_list_of_api_names
        To use scan mode, run command like below:
            cci task run qbrix_metadata_checker --scan_mode true
    check below for more available cli options:
        metadata_type:
            optional in scan mode
            the type of metadata, usually you can just use the folder names, such as flows, quickActions and etc
            for the metadata live within object folders, use just the sub folder names, such as fields, recordTypes
        api_names: 
            optional in scan mode
            this can be a comma separated list of metadata api names, 
            for the metadata sits within object folder, 
                the first api name need to be in "object_api_name.metadata_api_name" format, 
                while the following ones can be the metadata_api_name only, it will use the last object_api_name you entered, 
                example of valid input: Case.field1__c,field2__c,account.field1__c,field2__c, 
                example of invalid input: field1__c,case.field2__c
        refresh_base:
            optional, default to True, 
            the script will refresh the cached base repos, 
            you can set to False to save time if you need to run the command multiple times
        check_myself:
            optional, default to False, and will be force to False in "scan_mode"
            sometimes, you got an error msg from deploy saying a metadata is missing,
            but in reality, it could possibly be in your QBrix with a different name
            well, if you are as lazy as me and don't want to look at the folder manually
            you can set this to true and check if the metadata is already included in your own QBrix
        pull_metadata:
            optional, default to "ask", available options are "pull", "ignore" and "ask", it will be force to "ignore" if "scan_mode" is true
            if "pull", it will just simply try to pull the metadata from your default org, or the org you defined in next option
            if "ignore", just simply not pull
            if "ask", the script will ask you if you want to pull after you see the results
        sfdx_u:
            if you want to pull from an org that are different than the default org set in sfdx, define it here
        scan_mode:
            optional, default to False,
            if set to True, it will scan all metadata in your current QBrix and try to see if they exists in any base QBrix
        dependency_flow:
            optional, default to "deploy_qbrix"
            Instead of using the deploy_qbrix to check source dependencies, you can design your own flow to include any QBrix you want, 
            usually use this to check your "Sibling QBrix"
        show_found_only:
            optional, default to False in search mode and default to True in scan mode
            decide whether or not to display the "metadata not found" info, usually turn on in scan mode to prevent too much display


    texts above are just the instructions, feel free to ignore, results are below:
    *******************
    """

    task_options = {
        "metadata_type": {
            "description": "type of metadata, usually would just be the folder name in force-app, with a few exceptions such as custom field, record type and etc",
            "required": False
        },
        "api_names": {
            "description": "a comma separated list of metadata api names",
            "required": False
        },
        "refresh_base": {
            "description": "Set to True if you want to refresh the base cache",
            "required": False,
            "default": True
        },
        "check_myself": {
            "description": "Set to True if you want to check if the metadata is already in your own QBrix too",
            "required": False,
            "default": False
        },
        "pull_metadata": {
            "description": "available options are 'pull', 'ignore' and 'ask', define whether or not you want to pull down the metadata that are not found a match, use 'ask' if you want to decide after you see the results",
            "required": False,
            "default": "ask"
        },
        "sfdx_u": {
            "description": "If you would like to pull metadata from an org that are different than the default org set in sfdx, define it here",
            "required": False
        },
        "scan_mode": {
            "description": "Set to True if you want to scan all metadata in your qbrix to see if they already exists in your bases (or even sibling qbrix)",
            "required": False,
            "default": False
        },
        "dependency_flow": {
            "description": "default is 'deploy_qbrix' but you can define another flow that calls any qbrix you want to check",
            "required": False
        },
        "show_found_only": {
            "description": "Set to True if you want to only display the metadata were found, usually for getting a cleaner results in scan mode",
            "required": False,
            "default": False
        },
    }




    def _init_options(self, kwargs):
        super(MetadataChecker, self)._init_options(kwargs)
        # define the "non-standard behaviors" for metadata types.
        self.metadata_types = {
            "fields": {
                "key": "CustomField",
            },
            "objects": {
                "key": "CustomObject",
                "meta_ext": "",
            },
            "lwc": {
                "key": "LightningComponentBundle",
                "meta_ext": "",
            },
            "aura": {
                "key": "AuraDefinitionBundle",
                "meta_ext": "",
            },
            "classes": {
                "key": "ApexClass",
                "meta_ext": ".cls-meta.xml",
            },
            "settings": {
                "key": "settings",
                "meta_ext": ".settings-meta.xml",
            },
        }

        try:
            # Initiate Options
            self.refresh_base = False if "refresh_base" in self.options and self.options["refresh_base"].lower() == "false" else True

            self.scan_mode = True if "scan_mode" in self.options and self.options["scan_mode"].lower() == "true" else False
            self.dependency_flow = self.options["dependency_flow"] if "dependency_flow" in self.options else "deploy_qbrix"

            self.check_myself = True if "check_myself" in self.options and self.options["check_myself"].lower() == "true" else False
            if self.scan_mode:
                self.check_myself = False

            self.pull_metadata = self.options["pull_metadata"].lower() if "pull_metadata" in self.options and self.options["pull_metadata"].lower() in {"pull","ignore"} else "ask"
            if self.scan_mode:
                self.pull_metadata = "ignore"

            self.show_found_only = True if self.scan_mode else False
            if "show_found_only" in self.options:
                self.show_found_only = True if self.options["show_found_only"].lower() == "true" else False

        except:
            print("Unable to initiate initial options and settings.")

    
    def _init_metadata_type_detail(self, metadata_type):
        # each type will have some details go with them to define the behaviors
        # usually, we will just use the folder name as the metadata types, so users can easily copy/paste from repo
        
        #init the obj
        self.metadata_type_detail = self.metadata_types[metadata_type.lower()].copy() if metadata_type.lower() in self.metadata_types else {}


        # the "key" is the metadata name we will be using when do the force:source:retrieve, by default, it will just be the folder name minus the ending "s"
        if not "key" in self.metadata_type_detail:
            self.metadata_type_detail["key"] = metadata_type[0:-1] if metadata_type.lower().endswith("s") else metadata_type

        # the "meta_ext" is the extension name of the metadata file, we use it to check if the file is indeed a valid metadata file. by default, it will be .{key}-meta.xml
        if not "meta_ext" in self.metadata_type_detail:
            self.metadata_type_detail["meta_ext"] = f".{self.options['metadata_type'][0:-1]}-meta.xml" if "in_obj" in self.metadata_type_detail else f".{self.metadata_type_detail['key']}-meta.xml"

        # define in which folder we will be searching for the metadata, usually will just be the metadata type
        if not "folder" in self.metadata_type_detail:
            self.metadata_type_detail["folder"] = metadata_type
        
        # for these special metadata types, they will sit within object folder, so we mark them by giving a "in_obj" key, and gave them special folder info
        if metadata_type.lower() in ["businessprocesses","compactlayouts","fields","listviews","recordtypes","weblinks"]:
            self.metadata_type_detail["in_obj"] = True
            if not "folder" in self.metadata_type_detail:
                self.metadata_type_detail["folder"] = f"objects/__object_api__/{self.options['metadata_type']}"


    def _refresh_base(self):
        if os.path.exists(self.cci_cache_path):
            for sub in os.listdir(self.cci_cache_path):
                shutil.rmtree(os.path.join(self.cci_cache_path, sub), ignore_errors=True)
        flow_coordinator = CliRuntime().get_flow(self.dependency_flow)



    def _find_base_folders(self):
        if os.path.exists(self.cci_cache_path):
            for base_folder in os.listdir(self.cci_cache_path):
                if not base_folder.startswith("QBrix"):
                    continue

                base_folder_path = os.path.join(self.cci_cache_path,base_folder)
                all_base_subdirs = [os.path.join(base_folder_path, d) for d in os.listdir(base_folder_path) if len(d) == 40]
                # find the latest version of the base
                latest_base_folder = max(all_base_subdirs, key=os.path.getmtime)

                self.base_folders.add(latest_base_folder)

        if self.check_myself:
            self.base_folders.add("./")


    def find_metadata(self, metadata_type, api_names):
        if not metadata_type:
            metadata_type = self.options["metadata_type"]

        if not api_names:
            api_names = self.options["api_names"]

        self._init_metadata_type_detail(metadata_type)

        # make sure the .cci/projects folder exists, that's where we search for metadata files/folders
        if not os.path.exists(self.cci_cache_path):
            log.error("cci path not found, it's likely because you haven't got the base qbrix repos cached in your project yet, try run the command again with --refresh_base true option")
            return

        object_api = ""
        meta_api = ""
        full_meta_api = ""
        to_pull = ""

        # allowing multiple api_names per command
        for full_meta_api in api_names.split(","):

            full_meta_api = full_meta_api.strip()
            meta_api = full_meta_api

            meta_results = ""

            # for the "in_obj" type of metadata, the object api name is required, so we need some method to validate user input.
            if("in_obj" in self.metadata_type_detail):
                api_name_parts = full_meta_api.split(".")
                
                # we do allow lazy users to do something like Case.field1,field2,field3, so they don't have to specify the object api name every time
                if len(api_name_parts) == 2:
                    object_api = api_name_parts[0]
                    meta_api = api_name_parts[1]
                elif len(api_name_parts) == 1:
                    if object_api:
                        meta_api = api_name_parts[0]
                        full_meta_api = f"{object_api}.{meta_api}"
                    else:
                        log.error(f"\n    invalid api name format for {full_meta_api}, please use object_api_name.metadata_api_name format for each metadata")
                        continue
                else:
                    log.error(f"\n    invalid api name format for {full_meta_api}, please use object_api_name.metadata_api_name format for each metadata")
                    continue

            # find the base folders
            for base_folder in self.base_folders:
                # check if the meta data exists in the base
                found_results = self._find_meta_in_base(full_meta_api, base_folder)
                if len(found_results):
                    meta_results += found_results
            
            if len(meta_results):
                log.info(f"\n    {full_meta_api} <{metadata_type}>")
                print(meta_results)
            else:
                if not self.show_found_only:
                    log.info(f"\n    no matching <{metadata_type}> found for {full_meta_api}")
                to_pull += f",{full_meta_api}"
        
        # if we did not set the pull_metadata in option, and there is some metadata missing, we will ask if you want to pull it down from source
        if to_pull and self.pull_metadata == "ask":
            do_we_pull = input("\n********\nSome of the metadata were not found anywhere, do you want to pull it down from your default org? (Y/n)")
            if not do_we_pull or do_we_pull.lower() == "y":
                self.pull_metadata = "pull"
        
        if to_pull and self.pull_metadata == "pull":
            my_cmd = f"sfdx force:source:retrieve -m {self.metadata_type_detail['key']}:{to_pull[1:]}"
            if "sfdx_u" in self.options:
                my_cmd += f" -u {self.options['sfdx_u']}"
            log.debug(f"Running pull command: {my_cmd}")
            pull_result = subprocess.run(my_cmd, shell=True, capture_output=True)

            str_output = pull_result.stdout.decode("utf-8")
            if "No results found" in str_output:
                log.error(str_output)
            else:
                log.info(str_output)


    def scan_metadata(self):
        for one_folder in ["force-app/main/default/","unpackaged/pre","unpackaged/post"]:
            one_folder_path = os.path.join("./",one_folder)
            for one_metadata_type in os.listdir(one_folder_path):
                # log.debug(f"check {one_metadata_type} in {one_folder}")
                one_metadata_type_path = os.path.join(one_folder_path, one_metadata_type)
                if not os.path.isdir(one_metadata_type_path):
                    continue

                if one_metadata_type in {"aura","lwc"}:
                    self.find_metadata(one_metadata_type,",".join(os.listdir(one_metadata_type_path)))
                    #do something
                
                elif one_metadata_type in {"objects"}:
                    for one_object in os.listdir(one_metadata_type_path):
                        one_object_path = os.path.join(one_metadata_type_path, one_object)
                        if not os.path.isdir(one_object_path):
                            continue

                        for one_obj_metadata in os.listdir(one_object_path):
                            one_obj_metadata_path = os.path.join(one_object_path, one_obj_metadata)
                            if not os.path.isdir(one_obj_metadata_path):
                                continue

                            api_names = ""
                            for one_file in os.listdir(one_obj_metadata_path):
                                if re.search(r'\.\w+\-meta\.xml$',one_file):
                                    my_api = re.sub(r'\.\w+\-meta\.xml$',"",one_file)
                                    api_names += f",{one_object}.{my_api}"
                            if api_names:
                                self.find_metadata(one_obj_metadata,api_names[1:])
                
                else:
                    api_names = ""
                    for one_file in os.listdir(one_metadata_type_path):
                        if re.search(r'\.\w+\-meta\.xml$',one_file):
                            my_api = re.sub(r'\.\w+\-meta\.xml$',"",one_file)
                            api_names += f",{my_api}"
                    if api_names:
                        self.find_metadata(one_metadata_type,api_names[1:])

        return



    def _find_meta_in_base(self, meta_api, base_path):
        # check if the meta_api contains object
        meta_api_parts = meta_api.split(".")
        object_api = ""

        # if there is a "." in the api name, it probably means the first part is the object api name while the second part is the api name of itself, let's assign them
        if len(meta_api_parts) >= 2:
            object_api = meta_api_parts[0]
            meta_api = meta_api_parts[1]

        my_results = ""

        # get the folder path of where the metadata should be
        for one_folder in ["force-app/main/default/","unpackaged/pre","unpackaged/post"]:
            meta_path = os.path.join(base_path, one_folder)
            meta_path = os.path.join(meta_path, self.metadata_type_detail["folder"].replace("__object_api__",object_api))

            
            if not os.path.exists(meta_path):
                continue
            
            # while this "one_file" could be a file or a folder
            for one_file in os.listdir(meta_path):
                
                file_meta = one_file.lower()

                # let's ignore the files that are not end with the "meta_ext"
                if self.metadata_type_detail["meta_ext"] and not file_meta.endswith(self.metadata_type_detail["meta_ext"].lower()):
                    continue
                
                # and ignore the non folder if "meta_ext" is empty
                if not self.metadata_type_detail["meta_ext"] and "." in file_meta:
                    continue

                file_meta = file_meta.replace(self.metadata_type_detail["meta_ext"].lower(),"")
                file_meta_plain = file_meta

                if object_api:
                    file_meta_plain = file_meta.replace(object_api.lower(),"")[1:]
                    if not "in_obj" in self.metadata_type_detail:
                        if not file_meta.startswith(object_api.lower()):
                            continue
                
                if file_meta_plain == meta_api.lower():
                    my_results += f"        -- EXACT API name: {one_file} -- in {base_path.replace(self.cci_cache_path, '')[1:]}/{one_folder}\n"
                elif file_meta_plain.endswith(meta_api.lower()):
                    my_results += f"        -- found with prefix: {one_file} -- in {base_path.replace(self.cci_cache_path, '')[1:]}/{one_folder}\n"

        return my_results



    def _run_task(self):
        log.info(self.task_docs)

        # if refresh_base set to true, we will load the info of flow deploy_qbrix, which should trigger a cache of all source/base qbrixs, well, if the yml file is properly configured.
        if self.refresh_base:
            self._refresh_base()
        
        # get all base folders
        self._find_base_folders()

        if self.scan_mode:
            self.scan_metadata()
        else:
            self.find_metadata('','')

        