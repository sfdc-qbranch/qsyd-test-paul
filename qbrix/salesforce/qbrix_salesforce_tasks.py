import base64
import json
import os
import pathlib
import subprocess
import yaml
from abc import ABC
from datetime import datetime, timedelta

import click
from cumulusci.core.config import ScratchOrgConfig, TaskConfig
from cumulusci.core.dependencies.dependencies import PackageVersionIdDependency, PackageNamespaceVersionDependency, UnmanagedGitHubRefDependency
from cumulusci.core.dependencies.resolvers import dependency_filter_ignore_deps, get_static_dependencies
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.core.flowrunner import FlowCoordinator
from cumulusci.tasks.salesforce.update_dependencies import UpdateDependencies
from cumulusci.tasks.sfdx import SFDXOrgTask
from cumulusci.core.tasks import BaseTask
from qbrix.tools.data.qbrix_analytics import AnalyticsManager
from qbrix.tools.shared.qbrix_cci_tasks import run_cci_flow, run_cci_task
from qbrix.tools.shared.qbrix_console_utils import init_logger
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.utils import process_list_of_pairs_dict_arg
from cumulusci.tasks.salesforce.sourcetracking import RetrieveChanges

from qbrix.tools.shared.qbrix_project_tasks import check_and_update_setting, get_packages_in_stack
from qbrix.tools.health.qbrix_project_checks import run_experience_cloud_checks, run_einstein_checks, run_crm_analytics_checks
from qbrix.tools.utils.qbrix_orgconfig_hydrate import NGOrgConfig

log = init_logger()
now = datetime.now()


def salesforce_query(soql, org_config, raw_return=False):
    if soql != "" and org_config is not None:
        dx_command = f"sfdx force:data:soql:query -q \"{soql}\" --json "

        subprocess.run(f"sfdx config:set instanceUrl={org_config.instance_url}", shell=True, capture_output=True)

        if isinstance(org_config, ScratchOrgConfig):
            dx_command += " -u {username}".format(username=org_config.username)
        else:
            dx_command += " -u {username}".format(username=org_config.access_token)

        result = subprocess.run(dx_command, shell=True, capture_output=True)
        subprocess.run("sfdx config:unset instanceUrl", shell=True, capture_output=True)

        if result.returncode > 0:
            if result.stderr:
                error_detail = result.stderr.decode("UTF-8")
                log.error(f"Salesforce Query Error - Details: {error_detail}")
            else:
                log.error("Salesforce Query Failed, although no error detail was returned.")

            return None

        json_result = json.loads(result.stdout)

        if json_result["result"]["totalSize"] >= 1:
            if raw_return:
                return json_result
            else:
                return json_result["result"]["records"][0][list(json_result["result"]["records"][0].keys())[1]]
        else:
            return None


def QbrixInstallCheck(qbrix_name, org_config):
    log.info(f"Checking for Qbrix: {qbrix_name}")
    subprocess.run(f"sfdx config:set instanceUrl={org_config.instance_url}", shell=True, capture_output=True)

    dx_soql = f"SELECT Id from xDO_Base_QBrix_Register__mdt WHERE xDO_Repository_URL__c LIKE '%{qbrix_name}%'"
    dx_command = f"sfdx force:data:soql:query -q \"{dx_soql}\" --json "

    if isinstance(org_config, ScratchOrgConfig):
        dx_command += " -u {username}".format(username=org_config.username)
    else:
        dx_command += " -u {username}".format(username=org_config.access_token)

    result = subprocess.run(dx_command, shell=True, capture_output=True)
    subprocess.run("sfdx config:unset instanceUrl", shell=True, capture_output=True)

    if result is None:
        log.error("Nothing was returned. Check that the org still exists and that you can login via cci.")
        return False

    json_result = json.loads(result.stdout)

    if 'result' not in json_result or len(json_result['result']) == 0:
        log.info("No Q Brix installed")
        return False

    if json_result["result"]["totalSize"] >= 1:
        log.info(f"{qbrix_name} is installed.")
        return True
    else:
        log.info(f"{qbrix_name} is NOT installed.")
        return False


def _time_since_modified(path):
    """
    Returns the time since the target file was last modified

    Args:
        path (str): Relative Path to the file

    Returns:
        timedelta: Time since the target file was last modified
    """

    timestamp = os.path.getmtime(str(path))
    last_modified = datetime.fromtimestamp(timestamp)
    return datetime.now() - last_modified


def _remove_missing_field_schema(submitted_dict, field_names):
    """
    Removes keys and related values from a submitted dict containing User fields and values, which are not present in the target org.

    Args:
        submitted_dict (dict): The submitted dict containing User fields and values
        field_names (list): The names of the User fields in the target org

    Returns:
        dict: The submitted dict containing User fields and values, with missing keys and values removed
    """

    submitted_fields = list(submitted_dict.keys())
    for key in submitted_fields:
        if key not in field_names or str(key).endswith("Id"):
            log.debug(f"The field with api name '{key}' has been removed from this deployment, as it is either not present (or accessible) in the target org or it cannot be used by this task.")
            del submitted_dict[key]
    return submitted_dict


class CreateUser(BaseSalesforceApiTask,NGOrgConfig, ABC):
    salesforce_task = True

    task_docs = """
    Overview: Creates a user or multiple user records in a target org.

    There are two modes for this task:

    Single Record: Within the step, add a task with options set for 'data', 'role', 'profile' and optionally 'permission_set_api_names', 'permission_set_group_api_names' and 'user_profile_image'. The 'path' option must not be defined as this will enable bulk mode and ignore anything you have set for the options mentioned.

    Bulk Mode: Create a .yml file within your project and provide the relative path to the file, within the 'path' option. If the path is left blank, single record mode will be used.

    Note: For both modes above, the option for 'upsert_field' must be set if you are not using External_ID__c

    See https://confluence.internal.salesforce.com/display/QNEXTGENDEMOS/User+Manager for additional help and templates.

    """

    task_options = {
        "org": {
            "description": "Org Alias for the target org",
            "required": False
        },
        "data": {
            "description": "Dictionary of Fields and Related Values. Use the API name for the field and then set the value accordingly.",
            "required": False
        },
        "role": {
            "description": "Name of the Role which the new user should have, e.g. CEO",
            "required": False
        },
        "profile": {
            "description": "Name of the Profile the new user should have. e.g. System Administrator",
            "required": False
        },
        "permission_set_api_names": {
            "description": "List of API names for the Permission Sets you want to apply to the newly created User",
            "required": False
        },
        "permission_set_group_api_names": {
            "description": "List of API names for the Permission Set Groups you want to apply to the newly created User",
            "required": False
        },
        "permission_set_license_api_names": {
            "description": "List of API names for the Permission Set Licenses you want to apply to the newly created User",
            "required": False
        },
        "user_profile_image": {
            "description": "Local file location for the image you want to assign to the user profile. (COMING SOON) Use the keyword AUTO to automatically generate an image for the user.",
            "required": False
        },
        "upsert_field": {
            "description": "API Name of the field you wish to use for upserts. Must be a unique field on the object. Defaults to External_ID__c",
            "required": False
        },
        "path": {
            "description": "Path to yml file containing user record entries. Setting this will ignore anything set for other options. Setting this enables bulk mode and ignores other options.",
            "required": False
        },
        "link_contact_record": {
            "description": "Links user to related Contact record, using firstname and lastname to lookup the record. Set to True to enable this feature.",
            "required": False
        },
        "manager_external_id": {
            "description": "External ID for the User record who is the manager for the current record",
            "required": False
        }
        ,
        "contact_external_id": {
            "description": "External ID for the contact record to associate to the community user",
            "required": False
        }
    }

    def _init_options(self, kwargs):
        super(CreateUser, self)._init_options(kwargs)
        
        
        self.data = process_list_of_pairs_dict_arg(self.options["data"]) if "data" in self.options else None
        self.role = self.options["role"] if "role" in self.options else None
        self.when = self.options["when"] if "role" in self.options else None
        self.profile = self.options["profile"] if "profile" in self.options else None
        self.permission_set_api_names = list(self.options["permission_set_api_names"]) if "permission_set_api_names" in self.options else None
        self.permission_set_group_api_names = list(self.options["permission_set_group_api_names"]) if "permission_set_group_api_names" in self.options else None
        self.permission_set_license_api_names = list(self.options["permission_set_license_api_names"]) if "permission_set_license_api_names" in self.options else None
        self.user_profile_image = self.options["user_profile_image"] if "user_profile_image" in self.options else None
        self.upsert_field = self.options["upsert_field"] if "upsert_field" in self.options else "External_ID__c"
        self.path = self.options["path"] if "path" in self.options else None
        self.link_contact_record = self.options["link_contact_record"] if "link_contact_record" in self.options else False
        self.manager_external_id = self.options["manager_external_id"] if "manager_external_id" in self.options else False
        self.contact_external_id = self.options["contact_external_id"] if "contact_external_id" in self.options else False
        self.ignore_failures = bool(self.options["ignore_failures"]) if "ignore_failures" in self.options else False

    def _get_user_desc(self, tmp_file_location=None):
        """
        Gets the Object Describe information for the User Object in the target org. This is also cached via a file in .qbrix directory.

        Args:
            tmp_file_location (str): (optional) Location of the file to cache the object describe information. Defaults to .qbrix/user_object_desc.json

        Returns:
            dict: The Object Describe information for the User Object in the target org
        """

        if not tmp_file_location:
            tmp_file_location = ".qbrix/user_object_desc.json"

        if os.path.exists(tmp_file_location) and _time_since_modified(tmp_file_location) <= timedelta(minutes=10):
            log.info("Loading cached File...")
            with open(tmp_file_location, "r") as user_detail_file:
                return json.load(user_detail_file)
        else:
            log.info("Loading info from org and creating cached File...")
            api = self.sf
            user_details = api.User.describe()
            if not os.path.exists(".qbrix"):
                os.mkdir(".qbrix")
            with open(tmp_file_location, "w") as user_detail_file:
                json.dump(user_details, user_detail_file)
            return user_details

    def _ensure_required_fields(self, submitted_dict, field_names, role, profile, manager=None, contact=None):
        """
        Checks that all required fields have a value, even if none were passed in, except for FirstName and LastName which are required.

        Args:
            submitted_dict (dict): The dictionary of submitted values
            field_names (list): The list of field names to check
            role (str): The role of the user
            profile (str): The profile of the user
            manager (str): The manager of the user
            contact (str): The contact of the user

        Raises:
            Exception: If a required field is missing in the submitted_dict or if a required field is missing in the field_names list.

        """

        if "FirstName" not in submitted_dict.keys() or "LastName" not in submitted_dict.keys():
            raise Exception("You must provide at least a FirstName and LastName.")

        if "External_ID__c" not in submitted_dict.keys() and "External_ID__c" in field_names:
            log.debug("External ID (API Name External_ID__c) missing for User. It is HIGHLY recommended that an External ID is provided for all user records you are created. Please review your configuration.")

        if "Key_User__c" not in submitted_dict.keys() and "Key_User__c" in field_names:
            log.debug("Key User Field has not been defined and this is recommended for Key Demo Persona records by setting the Key_User__c field.")

        if "Alias" not in submitted_dict.keys():
            generated_alias = str(submitted_dict.get("FirstName"))[0:1].lower() + str(submitted_dict.get("LastName"))[0:4].lower()
            submitted_dict.update({"Alias": generated_alias})
        else:
            trimmed_alias = str(submitted_dict.get("Alias"))[0:7]
            submitted_dict.update({"Alias": trimmed_alias})

        if "DefaultGroupNotificationFrequency" not in submitted_dict.keys():
            submitted_dict.update({"DefaultGroupNotificationFrequency": "N"})

        if "DigestFrequency" not in submitted_dict.keys():
            submitted_dict.update({"DigestFrequency": "N"})

        if "Email" not in submitted_dict.keys():
            generated_email = f"{submitted_dict.get('FirstName').lower()}.{submitted_dict.get('LastName').lower()}{now.strftime('%H%M%S')}@example.com"
            submitted_dict.update({"Email": generated_email})

        if "Username" not in submitted_dict.keys():
            generated_username = f"{submitted_dict.get('FirstName').lower()}{submitted_dict.get('LastName').lower()}{now.strftime('%m%Y%H%M%S%f')}@example.com"
            submitted_dict.update({"Username": generated_username})

        if "EmailEncodingKey" not in submitted_dict.keys():
            submitted_dict.update({"EmailEncodingKey": "UTF-8"})

        if "LanguageLocaleKey" not in submitted_dict.keys():
            submitted_dict.update({"LanguageLocaleKey": "en_US"})

        if "LocaleSidKey" not in submitted_dict.keys():
            submitted_dict.update({"LocaleSidKey": "en_US"})

        if "TimeZoneSidKey" not in submitted_dict.keys():
            submitted_dict.update({"TimeZoneSidKey": "America/Los_Angeles"})

        if "UserPermissionsInteractionUser" not in submitted_dict.keys():
            submitted_dict.update({"UserPermissionsInteractionUser": False})

        if "UserPermissionsMarketingUser" not in submitted_dict.keys():
            submitted_dict.update({"UserPermissionsMarketingUser": False})

        if "UserPermissionsOfflineUser" not in submitted_dict.keys():
            submitted_dict.update({"UserPermissionsOfflineUser": False})

        if "UserPermissionsKnowledgeUser" not in submitted_dict.keys():
            submitted_dict.update({"UserPermissionsKnowledgeUser": False})

        api = self.sf

        # Lookup Role
        if role:
            role_id = api.query(f"SELECT Id FROM UserRole WHERE Name = '{role}' LIMIT 1")
            if role_id["totalSize"] == 0:
                raise Exception("User Creation Failed to get Role ID for provided Role: " + role)
            else:
                submitted_dict.update({"UserRoleId": role_id["records"][0]["Id"]})

        # Lookup Profile
        profile_id = api.query(f"SELECT Id FROM Profile WHERE Name = '{profile}' LIMIT 1")
        if profile_id["totalSize"] == 0:
            raise Exception("User Creation Failed to get Profile ID for provided Profile: " + profile)
        if "ProfileId" not in submitted_dict.keys():
            submitted_dict.update({"ProfileId": profile_id["records"][0]["Id"]})

        # Lookup Manager
        if manager:
            manager_id = api.query(f"SELECT Id FROM User Where External_ID__c = '{manager}' LIMIT 1")
            if manager_id["totalSize"] == 0:
                log.debug(f"No User Record found for the manger external id provided. {manager}")
            else:
                submitted_dict.update({"ManagerId": manager_id["records"][0]["Id"]})

        # Lookup Contact
        if contact:
            contact_id = api.query(f"SELECT Id FROM Contact Where External_ID__c = '{contact}' LIMIT 1")
            if contact_id["totalSize"] == 0:
                log.debug(f"No Contact Record found for the contact external id provided. {contact}")
            else:
                submitted_dict.update({"ContactId": contact_id["records"][0]["Id"]})

        return submitted_dict

    def _load_data(self, submitted_dict):
        """
        Loads User Record from submitted dict with User field and value data. Returns a UserId if successful.
        """

        api = self.sf

        print(submitted_dict)

        # Check If Upsert Can be Used
        if self.upsert_field in submitted_dict.keys() and "ContactId" not in submitted_dict.keys():
            log.info("UPSERT MODE")
            external_id_value = submitted_dict.get(self.upsert_field)
            clean_dict_for_upsert = submitted_dict
            del clean_dict_for_upsert[self.upsert_field]

            upsert_result = api.User.upsert(f"{self.upsert_field}/{external_id_value}", clean_dict_for_upsert)
            if str(upsert_result).startswith("2"):
                log.info("Upsert Completed! Loading record information...")
                print(f"SELECT Id FROM User WHERE {self.upsert_field} = '{external_id_value}' AND IsActive = True LIMIT 1")
                user_info = api.query(f"SELECT Id FROM User WHERE {self.upsert_field} = '{external_id_value}' AND IsActive = True LIMIT 1")
                if user_info["totalSize"] == 0:
                    log.error("User Upsert Failed. Skipping user...")
                    return
                else:
                    return user_info["records"][0]["Id"]
            else:
                log.error("Upsert Failed. Skipping Record...")
                return

        # Check for Existing User and create or update a record as required
        External_ID = submitted_dict.get(self.upsert_field)
        where_clause = f"(FirstName = '{submitted_dict.get('FirstName')}' AND LastName = '{submitted_dict.get('LastName')}') AND IsActive = True"
        if External_ID:
            where_clause = f"((FirstName = '{submitted_dict.get('FirstName')}' AND LastName = '{submitted_dict.get('LastName')}') OR ({self.upsert_field} = '{submitted_dict.get(self.upsert_field)}')) AND IsActive = True "
        user_lookup = api.query(f"SELECT Id FROM User WHERE {where_clause} LIMIT 1")
        if user_lookup["totalSize"] == 0:
            log.info("Creating new User record...")
            try:
                result = api.User.create(submitted_dict)
            except Exception as e:
                log.error(f"Record Failed to Create. Details: {e}")
                return
            if result["id"]:
                log.info("Record Created with ID: " + result["id"])
                return result["id"]
            else:
                log.error("Record Failed to Create.")
                return
        else:
            user_id = user_lookup["records"][0]["Id"]
            try:
                result = api.User.update(user_id, submitted_dict)
            except Exception as e:
                log.error(f"Record Failed to Update. Details: {e}")
                return
            if str(result).startswith("2"):
                log.info("Record Updated!")
                return user_id
            else:
                log.error("Record Failed to Update. User ID: " + user_id)
                return

    def _upload_user_profile_image(self, user_id, path_to_image):
        """
        Uploads and assigns a user profile image
        """

        if str(path_to_image).upper() == "AUTO":
            log.info("This feature is currently being built. Please provide the path to an image instead.")
            return

        if not os.path.exists(path_to_image):
            log.error(f"Image file path ({path_to_image}) does not exist. Please check file path and try again.")
        else:
            try:
                api = self.sf
                path = pathlib.Path(path_to_image)
                photo_id = api.ContentVersion.create(
                    {
                        "PathOnClient": path.name,
                        "Title": path.stem,
                        "VersionData": base64.b64encode(path.read_bytes()).decode("utf-8"),
                    }
                )

                content_version_id = photo_id["id"]
                content_document_id = api.query(f"SELECT Id, ContentDocumentId FROM ContentVersion WHERE Id = '{content_version_id}'")["records"][0]["ContentDocumentId"]

                api.restful(
                    f"connect/user-profiles/{user_id}/photo",
                    data=json.dumps({"fileId": content_document_id}),
                    method="POST",
                )
            except Exception as e:
                log.error(f"Upload Failed. Error details: {e}")

            log.info("Image Uploaded and assigned!")

    def _assign_permission(self, mode, user_id, api_names,ignore_failures=False):
        """
        Assigns Permission Sets or Permission Set Groups or Permission Set Licenses based on the mode. 

        Permission Sets use mode: PERMISSIONSET
        Permission Set Groups use mode: PERMISSIONSETGROUP
        Permission Set Licenses use mode: PERMISSIONSETLICENSE

        User Record ID and the api names (as a list) are also required.
        """
        if mode:
            if str(mode).upper() == "PERMISSIONSET":
                object_name = "PermissionSet"
                message_name = "Permission Set"
                lookup_field = "Name"
                assignment_field = "PermissionSetId"
                assignment_object = "PermissionSetAssignment"

            if str(mode).upper() == "PERMISSIONSETGROUP":
                object_name = "PermissionSetGroup"
                message_name = "Permission Set Group"
                lookup_field = "DeveloperName"
                assignment_field = "PermissionSetGroupId"
                assignment_object = "PermissionSetAssignment"

            if str(mode).upper() == "PERMISSIONSETLICENSE":
                object_name = "PermissionSetLicense"
                message_name = "Permission Set License"
                lookup_field = "DeveloperName"
                assignment_field = "PermissionSetLicenseId"
                assignment_object = "PermissionSetLicenseAssign"

            if str(mode).upper() != "PERMISSIONSETGROUP" and str(mode).upper() != "PERMISSIONSET" and str(mode).upper() != "PERMISSIONSETLICENSE":
                log.error(f"Error: Invalid mode passed. Only Permission Sets (PERMISSIONSET) or Permission Set Groups (PERMISSIONSETGROUP) or Permission Set Licenses (PERMISSIONSETLICENSE) are supported. Mode passed: {mode}")
                return False

            
            # Loop Through Permission Set Names
            for perm in list(api_names):
                    
                    try:
                        
                        api = self.sf

                        # Check for labels and non api names
                        if " " in perm:
                            log.debug(f"{message_name} {perm} is not a valid api name for a {message_name}. Please check the api names are valid and try again. Continuing to next record.")
                            continue

                        # Check Permission Set Exists
                        permission_set_query = api.query(f"SELECT Id FROM {object_name} WHERE {lookup_field} = '{perm}' LIMIT 1")
                        if permission_set_query["totalSize"] == 0:
                            log.debug(f"{message_name} with api name {perm} was not found in the target org, skipping assignment.")
                            continue
                        else:
                            permission_set_id = permission_set_query["records"][0]["Id"]

                        # Check for existing Permission Set, Group or License has been already assigned
                        permission_set_assignment_query = api.query(f"SELECT Id FROM {assignment_object} WHERE AssigneeId = '{user_id}' AND {assignment_field} = '{permission_set_id}' LIMIT 1")
                        if permission_set_assignment_query["totalSize"] == 1:
                            log.info(f"{message_name} with api name {perm} has already been assigned to the user. Skipping...")
                            continue

                        permset_creation_result = None
                        if str(mode).upper() != "PERMISSIONSETLICENSE":
                            # Create Permission Set Assignment
                            permset_creation_result = api.PermissionSetAssignment.create(
                                {
                                    "AssigneeId": user_id,
                                    str(assignment_field): permission_set_id
                                }
                            )
                        else:
                            # Create Permission Set License Assignment
                            permset_creation_result = api.PermissionSetLicenseAssign.create(
                                {
                                    "AssigneeId": user_id,
                                    str(assignment_field): permission_set_id
                                }
                            )

                        if not permset_creation_result is None and permset_creation_result["id"]:
                            log.info(f"{message_name} (With API Name: {perm}) has been assigned (ID: {permset_creation_result['id']})!")
                        else:
                            log.error(f"{message_name} (With API Name: {perm}) failed to assign. Moving onto next {message_name} (if any). Details: {permset_creation_result}")
                            
                            if(ignore_failures):
                                continue
                            else:
                                return False

                    except Exception as e:
                        log.debug("Error: Failure in user upsert.")
                        log.debug(e)
                        if(ignore_failures==False):    
                            return False
                        
        else:
            log.debug("Error: No Mode was passed for processing. You must pass in a mode.")
            return False

        return True

    def _process_user_record(self, user_record_data, field_names):
        data = user_record_data["data"]
        role = user_record_data["role"] if "role" in dict(user_record_data).keys() else None
        profile = user_record_data["profile"]
        user_profile_image = user_record_data["user_profile_image"] if "user_profile_image" in dict(user_record_data).keys() else None
        permission_set_api_names = user_record_data["permission_set_api_names"] if "permission_set_api_names" in dict(user_record_data).keys() else None
        permission_set_group_api_names = user_record_data["permission_set_group_api_names"] if "permission_set_group_api_names" in dict(user_record_data).keys() else None
        permission_set_license_api_names = user_record_data["permission_set_license_api_names"] if "permission_set_license_api_names" in dict(user_record_data).keys() else None
        link_contact_record = user_record_data["link_contact_record"] if "link_contact_record" in dict(user_record_data).keys() else None
        manager = user_record_data["manager_external_id"] if "manager_external_id" in dict(user_record_data).keys() else None
        contact = user_record_data["contact_external_id"] if "contact_external_id" in dict(user_record_data).keys() else None
        if "ignore_failures" in dict(user_record_data).keys():
            ignore_failures = bool(user_record_data["ignore_failures"]) 
        else:
            ignore_failures =False

        log.info(f"Creating User with the following details: \n{json.dumps(data, indent=1, sort_keys=True)}")
        log.info("Preparing Data for User Record")

        # Clean Up Fields which are not available on the User object
        data = _remove_missing_field_schema(data, field_names)

        # Check and Update Required Fields
        data = self._ensure_required_fields(data, field_names, role, profile, manager, contact)

        # Link Contact Record
        if link_contact_record:
            data = self._link_contact_record(data)

        log.info("Data Ready to upload")

        # Load Data
        final_user_id = self._load_data(data)

        if final_user_id:
            log.info("Final User Record ID: " + final_user_id)

            # Handle Profile Image Upload
            if user_profile_image:
                log.info("Adding User Profile Image...")
                self._upload_user_profile_image(final_user_id, user_profile_image)

            # Handle Permissions
            # Load PSL First to make sure namespace access is ok
            if permission_set_license_api_names:
                log.info("Assigning Permission Set Licenses...")
                self._assign_permission("PERMISSIONSETLICENSE", final_user_id, permission_set_license_api_names,ignore_failures)
            if permission_set_api_names:
                log.info("Assigning Permission Sets...")
                self._assign_permission("PERMISSIONSET", final_user_id, permission_set_api_names,ignore_failures)

            if permission_set_group_api_names:
                log.info("Assigning Permission Set Groups...")
                self._assign_permission("PERMISSIONSETGROUP", final_user_id, permission_set_group_api_names,ignore_failures)

        else:
            log.error("User Failed to insert...skipping")

    def _link_contact_record(self, submitted_dict):
        """
        Links the related Contact Record using Firstname and Lastname.
        """

        api = self.sf
        contact_lookup = api.query(f"SELECT Id FROM Contact WHERE FirstName = '{submitted_dict['FirstName']}' AND LastName = '{submitted_dict['LastName']}' LIMIT 1")
        if contact_lookup["totalSize"] == 1:
            submitted_dict.update(
                {
                    "ContactId": contact_lookup["records"][0]["Id"]
                }
            )
            log.info(f"Linked Contact Record ID: {contact_lookup['records'][0]['Id']}")
        else:
            log.debug(f"No Contact was found with Firstname {submitted_dict['FirstName']} and Lastname {submitted_dict['LastName']}. Make sure you are inserting any required contact data into the org before running this task.")
        return submitted_dict

    def _run_task(self):
        api = self.sf
        
        #inject in the orgc_config pointers. We might be running the task directly 
        #e.g.: cci task run user_manager --path blah/blah.yml --org goat
        self._prepruntime()
        self._inject_max_runtime()

        if api is not None:
            # Check for invalid configuration
            if self.path and self.data:
                log.debug("A Path has been specified, which enabled Bulk Mode and ignores other settings which have been defined. Check help pages and update as required. Will continue running in Bulk Mode")

            # Get User Fields for Target Org
            user_desc = self._get_user_desc()
            field_names = [field['name'] for field in user_desc['fields']]

            # Enable bulk mode if path provided
            if self.path:
                log.info("BULK MODE ENABLED")

                if not os.path.exists(self.path):
                    raise Exception("Path to file cannot be found.")

                with open(self.path, "r") as file:
                    user_data = yaml.load(file, Loader=yaml.FullLoader)
                for user in user_data["users"]:
                        
                    user_record_data = user_data["users"][user]
                    self.logger.info(user_record_data)    
                    whenclauseskip=False
                    if("when" in user_record_data and not user_record_data['when'] is None):
                        #self.logger.info(user_record_data['when'])   
                        exp = user_record_data["when"].replace("org_config","self.org_config")
                        self.logger.info(exp)   
                        compliledcode = compile(exp, "<string>", "eval")
                        #no builtins = no __import__ # DO NOT allow globals
                        #restrict scope to expression - no builtins and only locals self
                        res = eval(compliledcode,{},{"self":self})
                
                        if(res == False):
                            whenclauseskip=True
                        
                    if(whenclauseskip==False):
                        self._process_user_record(user_record_data, field_names)
                    else:
                        self.logger.info(f"User create skipped for not meeting when clause::{exp}")
            else:
                log.info("SINGLE RECORD MODE ENABLED")

                if not self.data or not self.profile or not self.role:
                    log.error("When running in Single Record mode, you must provide values for the options data, role and profile as a minimum requirement.")
                else:
                    log.info(f"Creating User with the following details: \n{json.dumps(self.data, indent=1, sort_keys=True)}")
                    log.info("Preparing Data for User Record")

                    # Clean Up Fields which are not available on the User object
                    self.data = _remove_missing_field_schema(self.data, field_names)

                    # Check and Update Required Fields
                    self.data = self._ensure_required_fields(self.data, field_names, self.role, self.profile, self.manager_external_id, self.contact_external_id)

                    # Link Contact Record
                    if self.link_contact_record:
                        self.data = self._link_contact_record(self.data)

                    log.info("Data Ready to upload")

                    # Load Data
                    final_user_id = self._load_data(self.data)

                    if final_user_id:
                        log.info("Final User Record ID: " + final_user_id)

                        # Handle Profile Image Upload
                        if self.user_profile_image:
                            log.info("Adding User Profile Image...")
                            self._upload_user_profile_image(final_user_id, self.user_profile_image)

                        # Handle Permissions
                        # PSL First - to make sure namespace PSL get access first.
                        if self.permission_set_license_api_names:
                            log.info("Assigning Permission Set Licenses...")
                            self._assign_permission("PERMISSIONSETLICENSE", final_user_id, self.permission_set_license_api_names,self.ignore_failures)

                        if self.permission_set_api_names:
                            log.info("Assigning Permission Sets...")
                            self._assign_permission("PERMISSIONSET", final_user_id, self.permission_set_api_names,self.ignore_failures)

                        if self.permission_set_group_api_names:
                            log.info("Assigning Permission Set Groups...")
                            self._assign_permission("PERMISSIONSETGROUP", final_user_id, self.permission_set_group_api_names,self.ignore_failures)

                    else:
                        log.error("User Failed to insert. Skipping...")

        else:
            log.error("Failed to connect to Salesforce Org, please try again.")


class ListQBrix(SFDXOrgTask, ABC):
    task_options = {
    }

    salesforce_task = True

    def _init_options(self, kwargs):
        super(ListQBrix, self)._init_options(kwargs)
        self.options[
            "command"] = "force:data:soql:query -q 'SELECT MasterLabel,xDO_Version__c,xDO_Repository_URL__c from " \
                         "xDO_Base_QBrix_Register__mdt order by MasterLabel' "


class QBrixInstalled(BaseTask, ABC):
    task_options = {
        "qbrix_name": {
            "description": "Name of the Q Brix, starting with Qbrix-",
            "required": True
        }
    }

    salesforce_task = True

    def _init_options(self, kwargs):
        super(QBrixInstalled, self)._init_options(kwargs)
        self.qbrix_name = self.options["qbrix_name"]

    def _run_task(self):
        self.return_value = QbrixInstallCheck(self.qbrix_name, self.org_config)


class QUpdateDependencies(UpdateDependencies, ABC):

    def _install_dependency(self, dependency):

        if hasattr(dependency, "github") and len(dependency.github) > 1:
            if "qbrix" in dependency.github.lower():
                qbrix_name = dependency.github.rsplit('/', 1)[-1]
                if QbrixInstallCheck(qbrix_name, self.org_config):
                    return
                
        super()._install_dependency(dependency)

class QbrixDeployer(BaseSalesforceApiTask, ABC):
    task_docs = """
    Overview: Deploys the Q Brix if not already deployed
    """

    task_options = {
        "qbrix_name": {
            "description": "Name of the Q Brix, starting with Qbrix-",
            "required": True
        },
        "org": {
            "description": "Org alias",
            "required": False
        }
    }

    salesforce_task = True

    def _init_options(self, kwargs):
        super(QbrixDeployer, self)._init_options(kwargs)
        self.qbrix_name = self.options["qbrix_name"] if "qbrix_name" in self.options else None

    def _run_task(self):

        if not self.project_config.sources:
            print("No sources found in project config")
            return

        for name, value in self.project_config.sources.items():
            if 'github' in value and self.qbrix_name in value['github']:
                if not QbrixInstallCheck(self.qbrix_name, self.org_config):
                    coordinator = FlowCoordinator(self.project_config)
                    coordinator.run(f'{self.qbrix_name}:deploy_qbrix')
            else:
                print("Source name not found in Q Brix")
    

class PopulateRecentlyViewed(BaseSalesforceApiTask, ABC):
    task_docs = """
    Overview: Populates the Recently Viewed Listview with the most recent records for the given object(s)
    """

    task_options = {
        "org": {
            "description": "Org Alias for the target org",
            "required": False
        },
        "objects": {
            "description": "List of Objects which you want to update the recently viewed listview for",
            "required": True
        },
        "limit": {
            "description": "Limit for the objects, defaults to 500",
            "required": False
        },
    }

    def _init_options(self, kwargs):
        super(PopulateRecentlyViewed, self)._init_options(kwargs)
        self.objects = list(self.options["objects"]) if "objects" in self.options else None
        self.limit = self.options["limit"] if "limit" in self.options else 500
        self.unsupported_objects = [
            "User",
            "KnowledgeArticle"
        ]

    def _run_task(self):
        for obj in self.objects:
            if obj not in self.unsupported_objects:
                if str(obj).endswith("__c"):
                    custom_tab_result = self.sf.query_all(f"SELECT SObjectName FROM TabDefinition WHERE IsCustom = true AND SObjectName = '{obj}'")
                    if custom_tab_result.get("totalSize") == 0:
                        self.logger.info(f"{obj} does not have a Tab, so Recently Viewed cannot be automatically set. Skipping.")
                        continue

                query = f"SELECT Id FROM {obj} ORDER BY CreatedDate DESC LIMIT {self.limit} FOR VIEW"
                try:
                    self.sf.query_all(query)
                    self.logger.info(f"Updated Recently Viewed List for {obj}")
                except Exception as e:
                    self.logger.error(f"Error updating Recently Viewed List for {obj}: {e}")


class UploadFiles(BaseSalesforceApiTask, ABC):
    task_docs = """
    Uploads files from a given directory to Salesforce using a where clause to find a specific record.
    """

    task_options = {
        "org": {
            "description": "Org Alias for the target org",
            "required": False
        },
        "object": {
            "description": "The object to search against, for example Contact",
            "required": False
        },
        "where": {
            "description": "The Where Clause for the soql statement which locates the record you want to relate files to, for example External_ID__c = 'SDO_CONTACT_001' ",
            "required": False
        },
        "path": {
            "description": "Relative Path to the files you want to upload for the record found using the where clause ",
            "required": True
        },
        "library": {
            "description": "Name of library if uploading to a library",
            "required": False
        },
         "exclude_extension": {
            "description": "Exclued the file extension from the title",
            "required": False
        }
    }

    def _init_options(self, kwargs):
        super(UploadFiles, self)._init_options(kwargs)
        self.object = self.options["object"] if "object" in self.options else None
        self.where = self.options["where"] if "where" in self.options else None
        self.path = self.options["path"] if "path" in self.options else None
        self.library = self.options["library"] if "library" in self.options else None
        
        if "exclude_extension" in self.options:
            self.exclude_extension = bool(self.options["exclude_extension"]) 
        else:
            self.exclude_extension = False

    def create_document_link(self, content_doc_id, entity_id):
        """
        Creates a document link between a ContentDocument and a given Entity
        """

        record_lookup = self.sf.query(f"SELECT Id FROM ContentDocumentLink WHERE LinkedEntityId = '{entity_id}' AND ContentDocumentId = '{content_doc_id}'")
        if record_lookup['totalSize'] == 0:
            content_document_link_data = {
                'ContentDocumentId': content_doc_id,
                'LinkedEntityId': entity_id,
                'Visibility': 'AllUsers'
            }
            self.sf.ContentDocumentLink.create(content_document_link_data)

    def create_public_file_link(self, content_version_id, file_name):
        """
        Generates a public link for a given content version and file name
        """

        record_lookup = self.sf.query(f"SELECT Id FROM ContentDistribution WHERE ContentVersionId = '{content_version_id}'")
        if record_lookup['totalSize'] == 0:
            content_version_data = {
                'Name': file_name,
                'ContentVersionId': content_version_id,
                'PreferencesAllowViewInBrowser': True
            }
            self.sf.ContentDistribution.create(content_version_data)

    def upload_files_to_salesforce(self):
        """
        Uploads all files from the specified directory to the Salesforce and associates them as required.
        """
        self.logger.info("\nStarting File Upload:")

        # Query Salesforce to find the record ID that matches the where clause
        multi_record = False
        record_id = None
        if self.where:
            record = self.sf.query(f"SELECT Id FROM {self.object} WHERE {self.where}")
            if record['totalSize'] == 0:
                self.logger.error(f"No record(s) found for {self.object} with the specified where clause '{self.where}'. Skipping File.")
            elif record['totalSize'] == 1:
                record_id = record['records'][0]['Id']
                self.logger.info(f" -> Single Record Located with ID: {record_id}")
            elif record['totalSize'] > 1:
                self.logger.info(" -> Multiple Record Association Enabled")
                multi_record = True

        # Loop through each file in the directory
        for filename in os.listdir(self.path):
            # Check File Was not Already Uploaded
            self.logger.info(f"\nChecking for existing file called {filename}:")
            content_document_id = None
            existing_file = self.sf.query(f"SELECT Id, ContentDocumentId FROM ContentVersion WHERE PathOnClient = '{filename}' OR Title = '{filename}' LIMIT 1")
            if existing_file['totalSize'] > 0:
                content_document_id = existing_file['records'][0]['ContentDocumentId']
                self.logger.info(f" -> File already uploaded. Document Id: {content_document_id}")
            else:
                self.logger.info(" -> File was not found in target org")

                # Upload File and create new ContentVersion
                self.logger.info(f"\nUploading {filename}:")
                file_path = os.path.join(self.path, filename)
                with open(file_path, 'rb') as f:
                    file_contents = f.read()

                # Convert the file contents to base64 encoding
                base64_file_contents = base64.b64encode(file_contents).decode('utf-8')
                
                title=filename
                if(self.exclude_extension):
                    filebase=os.path.basename(filename)
                    title=os.path.splitext(filebase)[0]
                    
                
                    

                content_version_data = {
                    'Title': title,
                    'VersionData': base64_file_contents,
                    'PathOnClient': filename
                }

                content_version = self.sf.ContentVersion.create(content_version_data)
                content_document_id = self.sf.query(f"SELECT ContentDocumentId FROM ContentVersion WHERE Id = '{content_version['id']}'")['records'][0]['ContentDocumentId']

            # Create Required Relationships
            self.logger.info(f"\nChecking for creating Document Links")
            if self.where and record_id and multi_record == False:
                self.logger.info(f" -> Linking to Record: {record_id}")
                self.create_document_link(content_document_id, record_id)

            if self.where and multi_record == True and record['records']:
                for r in record['records']:
                    if r["Id"]:
                        self.logger.info(f" -> Linking to Record: {r['Id']}")
                        self.create_document_link(content_document_id, r["Id"])

            if self.library:
                workspace_record = self.sf.query(f"SELECT Id, RootContentFolderId FROM ContentWorkspace WHERE Name = '{self.library}' LIMIT 1")
                if workspace_record['totalSize'] == 0:
                    self.logger.info(f" -> {self.library} was not found. Creating new Library")
                    workspace_record = self.sf.ContentWorkspace.create({
                        'name': self.library
                    })
                    if workspace_record and workspace_record['id']:
                        self.logger.info(f" -> Saving to Library called: {self.library}")
                        self.create_document_link(content_document_id, workspace_record['id'])
                else:
                    self.logger.info(f" -> Saving to Library called: {self.library}")
                    self.create_document_link(content_document_id, workspace_record['records'][0]['Id'])

            self.logger.info(f" -> Upload Complete!")

    def _run_task(self):
        if (self.object and not self.where) or (not self.object and self.where):
            self.logger.error("You must specify both the Object and Where options if you want to associate to records. Cannot run task.")
            return

        self.upload_files_to_salesforce()


class ComparePackages(BaseSalesforceApiTask, ABC):
    task_docs = """
    Compares Packages referenced in the local project or local stack with packages currently listed within a target org
    """

    task_options = {
        "org": {
            "description": "Org Alias for the target org",
            "required": False
        },
        "local_project": {
            "description": "When True, only compares packages declared within the current project and not the stack of Q Brix",
            "required": False
        },
        "show_all_matches": {
            "description": "When True, output will show all matches not just those which require action. Defaults to False which only shows matches which require action",
            "required": False
        },
    }

    def _init_options(self, kwargs):
        super(ComparePackages, self)._init_options(kwargs)
        self.local_project = self.options["local_project"] if "local_project" in self.options else False
        self.show_all_matches = self.options["show_all_matches"] if "show_all_matches" in self.options else False

    def _run_task(self):
        # Get Package List
        self.logger.info("\nSearching for Package Version IDs")

        package_list = []

        if self.local_project:
            package_list = get_packages_in_stack(True, False)
        else:
            package_list = get_packages_in_stack(False, self.local_project)

        if len(package_list) > 0:
            self.logger.info(f"{len(package_list)} packages found")
        else:
            self.logger.info("No Package References Found")
            return

        # Get Package List from Org
        self.logger.info("\nGetting Installed Packages from Org and comparing")
        soql = "SELECT SubscriberPackage.Name, SubscriberPackageVersionId FROM InstalledSubscriberPackage ORDER BY SubscriberPackage.Name"
        toolingendpoint = 'query?q='
        results = self.sf.toolingexecute(f"{toolingendpoint}{soql.replace(' ', '+')}")
        org_packages = []
        if results['totalSize'] > 0:
            self.logger.info(f"{results['totalSize']} Packages Found in Target Org")
            for result in results["records"]:
                if result["SubscriberPackageVersionId"]:
                    org_packages.append((result["SubscriberPackageVersionId"], result['SubscriberPackage']['Name']))
        else:
            self.logger.info("No Packages found in org.")
            return

        # Compare Lists
        for package, qbrix_name in package_list:
            if self.show_all_matches:
                self.logger.info(f"\nChecking Package ID: {package} from {qbrix_name}:")

            package_found = False
            for package_id, package_name in org_packages:
                if package == package_id:
                    package_found = True
                    if self.show_all_matches:
                        self.logger.info(f" -> Found Package in Org, with name: {package_name}")
                    break

            if not package_found:
                if not self.show_all_matches:
                    self.logger.info(f"\nChecking Package ID: {package} from {qbrix_name}:")
                self.logger.info(" -> ACTION - Check this package ID within the related Q Brix and update if required.")


class QRetrieveChanges(RetrieveChanges):
    """
    Adds Q Brix custom logic to the Retrieve Changes Task
    """

    def _get_changes(self):
        changes = super()._get_changes()

        if changes:
            filtered = self._filter_changes(changes)[0]
            self.filtered = filtered
        else:
            self.filtered = None

        return changes

    def _run_task(self):
        # Add your custom logic here before or after the original implementation

        # Call the original _run_task method
        super()._run_task()

        # Add your custom logic here after the original implementation

        self.logger.info("Running Q Brix Checks...")
        member_types = set(change['MemberType'] for change in self.filtered)

        if "WaveDataset" in member_types:
            run_crm_analytics_checks(self.org_config.name)

        if "Bot" in member_types:
            run_einstein_checks()

        if "ExperienceBundle" in member_types:
            run_experience_cloud_checks()

        self.logger.info("Checks complete!")
