import datetime
import filecmp
import glob
import json
import os
import re
import shutil
import subprocess
import yaml
from io import BytesIO
from os.path import exists
import tempfile
from typing import Optional
from urllib.request import urlopen
from zipfile import ZipFile
import xml.etree.ElementTree as ET
from xml.dom import minidom

from qbrix.tools.shared.qbrix_json_tasks import update_json_file_value, get_json_file_value, remove_json_entry
from qbrix.tools.shared.qbrix_console_utils import init_logger
from qbrix.tools.utils.qbrix_fart import FART
from qbrix.tools.shared.qbrix_cci_tasks import rebuild_cci_cache
from qbrix.tools.shared.qbrix_shared_checks import is_github_url

log = init_logger()

DEFAULT_UPDATE_LOCATION = "https://qbrix-core.herokuapp.com/qbrix/q_update_package.zip"


def replace_file_text(file_location, search_string, replacement_string, show_info=False, number_of_replacements=-1):
    """ Replaces a string value within a given file

    Args:
        file_location (str): Relative path and file name of the file you want to replace text within
        search_string (str): The string value to find and replace within the given file content
        replacement_string (str): The replacement String value
        show_info (bool): When True, this will output information about the string value being modified.
        number_of_replacements (int): The total number of replacements to process, for example 1 would only replace the first instance of the search string in the file. Default is -1 which means replace all.
    """

    if not os.path.isfile(file_location):
        raise Exception(f"Error: File Path does not exist or you do not have access to the given file path. Please check this file path and update as required: {file_location}")

    try:
        if show_info:
            log.info(f"Checking {file_location}...")
        with open(f"{file_location}", "r") as tmpFile:
            file_contents = tmpFile.read()
    except Exception as e:
        raise Exception(f"There was an error opening the file with path: {file_location}. Please check the file still exists and that you have access to read it. Error detail: {e}")

    if search_string not in file_contents:
        return

    if show_info:
        log.info(f"Searching for all references to '{search_string}' and replacing with '{replacement_string}'.")

    updated_file_contents = file_contents.replace(f"{search_string}", f"{replacement_string}", number_of_replacements)

    try:
        with open(f"{file_location}", "w") as updated_file:
            updated_file.seek(0)
            updated_file.write(updated_file_contents)
    except Exception as e:
        raise Exception(f"There was an error updating the file with path: {file_location}. Please check the file still exists and that you have access to edit it. Error detail: {e}")


def get_qbrix_repo_url() -> str:
    """
    Get Repo URL for current Q Brix. If no .git has been linked to the given project, then user is prompted for url.

    Returns:
        str: GitHub repo url for the current Q Brix.
    """

    result = None
    try:
        result = subprocess.run("git config --get remote.origin.url", shell=True, capture_output=True).stdout
    except Exception as e:
        log.error(f"Unable to access GitHub Repository connected to this project. Please check that you have an internet connection and access to the GitHub Repository and you have git installed on your device. Error Detail: {e}")

    if not result:
        repo_url = input("Please Enter the complete URL for the Q brix Repo which should be linked to this project (e.g. https://www.github.com/sfdc-qbranch/Qbrix-1-repo): ")

        if repo_url == "" or repo_url is None:
            raise Exception("No GitHub Repo URL was found or entered into the prompt.")

        if not is_github_url(repo_url):
            raise Exception("URL Must be a valid Github.com URL to a Github repo.")
    else:
        repo_url = result.decode('utf-8').rstrip().replace(".git", "")

    return repo_url


def advanced_feature_match(check_value, list_value):
    """Checks for a given scratch org feature containing a : within a list of scratch org features. If the feature already exists, this return True
    otherwise False is returned.

    Args:
        check_value (str): The string value of a scratch org feature to check
        list_value (list(str)): The list of scratch org features to check against

    Returns:
        bool: True if match found in list, False if not
    """

    if ":" not in check_value:
        log.debug("Feature was passed to advanced feature match which does not match format expected.")
        return

    chk = False
    for substring in list_value:
        if substring.split(":")[0] == check_value.split(":")[0]:
            chk = True

    return chk


def check_and_delete_dir(dir_path):
    """Deletes a directory (and all contents) if it exists. Returns True if folder has been deleted.

    Args:
        dir_path (str): Relative path to the directory within the project

    Returns:
        bool: True when directory is deleted or the directory does not exist. False if there has been an issue.
    """

    # Run initial Checks
    if not os.path.exists(dir_path):
        log.info("Directory already appears to have been removed or does not exist.")
        return True

    if not os.path.isdir(dir_path):
        log.error(f"The given path ({dir_path}) is not a directory, stopping additional processing.")
        return False

    # Remove Directory and subdirectories
    try:
        shutil.rmtree(f"{dir_path}")
        log.info(f"Deleted {dir_path} and related sub-directories and files (if any)")
        return True
    except Exception as e:
        log.error(f"Unable to delete directory with path: {dir_path}. {e}")
        return False


def check_and_delete_file(file_path):
    """Deletes a File if it exists. Returns True if File has been removed.

    Args:
        file_path (str): The relative path to the file you want to delete.

    Returns:
        bool: True if file has been deleted or did not exist, False if there was an issue.
    """

    if not os.path.exists(file_path):
        return True

    if not os.path.isfile(file_path):
        log.error(f"The File path provided ({file_path}) is not a valid path to a file. Stopping further processing")
        return False

    try:
        os.remove(f"{file_path}")
        log.info(f"File Deleted: {file_path}")
        return True
    except Exception as e:
        log.error(f"Unable to delete file: {file_path}. {e}")
        return False


def update_org_file_features(file_location, missing_features, auto: Optional[bool] = False):
    """Updates scratch org json file features with additional features.

    Args:
        file_location (str): Relative path to the scratch org json file.
        missing_features (list(str)): List of scratch org features which are missing.
        auto (bool): When True this does not ask the end user for confirmation to make changes.

    Returns:
        bool: True when the file has been updated or if there are no missing features to process.

    """

    if not os.path.exists(file_location):
        log.error(f"The provided file path ({file_location}) does not exist.")
        return False

    if not os.path.isfile(file_location) or not str(file_location).endswith(".json"):
        log.error(f"The provided file path ({file_location}) is not a valid json file.")
        return False

    if len(missing_features) == 0:
        return True

    if not auto:
        get_response = input(f"Would you like to append missing features to your {file_location} file? (y/n) Default y: ") or 'y'
    else:
        get_response = 'y'

    if get_response == 'y':
        log.info(f"Updating: {file_location}")

        try:
            with open(file_location) as json_file:
                json_file_data = json.load(json_file)

            # Get Existing Feature List
            current_features = json_file_data['features']
            current_features = [x.lower() for x in current_features]

            # De-Duplicate Feature Lists and Append to Clean List
            clean_feature_list = []
            for current_feature in current_features:
                if (":" not in current_feature and not current_feature.lower() in clean_feature_list) or (":" in current_feature and not advanced_feature_match(current_feature.lower(), clean_feature_list)):
                    clean_feature_list.append(current_feature.lower())

            for missing_feature in missing_features:
                if (":" not in missing_feature and not missing_feature.lower() in clean_feature_list) or (":" in missing_feature and not advanced_feature_match(missing_feature.lower(), clean_feature_list)):
                    clean_feature_list.append(missing_feature.lower())

            clean_feature_list.sort()

            # Update File
            json_file_data['features'] = clean_feature_list
            with open(file_location, "w") as nFile:
                json.dump(json_file_data, nFile, indent=2)

            log.info(f"Updated features in file: {file_location}")

            return True
        except Exception as e:
            log.error(f"[ERROR] Unable to update features in file: {file_location}. Error Message: {e}")
            return False


def find_missing_features(main_features_file, check_features_file):
    """Compares two json scratch org definition files and checks the main file has all the features which the
    check file has. You can then optionally update the current project file with missing features.

        Args:
            main_features_file (str): Relative path to the scratch org json file which will be updated.
            check_features_file (str): Relative path to the scratch org json file which be used to compare to.

        Returns:
            list(str): List of missing scratch org features

    """

    if not os.path.exists(main_features_file):
        raise Exception(f"The provided file path for the Main File, located at ({main_features_file}), does not exist.")

    if not os.path.exists(check_features_file):
        raise Exception(f"The provided file path for the Comparison File, located at ({check_features_file}), does not exist.")

    log.info(f"Feature Check: Comparing {main_features_file} to {check_features_file}")

    # Init Missing Features List
    missing_features = []

    try:
        # Load Main File
        with open(main_features_file) as main_json_file:
            main_json_file_data = json.load(main_json_file)

        if not main_json_file_data['features']:
            raise Exception(f"[ERROR] No features found in file: {main_json_file}. Check the file and try again.")

        main_comparison_list = main_json_file_data['features']
        main_comparison_list = [x.lower() for x in main_comparison_list]

        # Load Comparison File
        with open(check_features_file) as check_json_file:
            check_json_file_data = json.load(check_json_file)

        if check_json_file_data['features'] is None:
            raise Exception(f"[ERROR] No features found in file: {check_json_file}. Check the file and try again.")

        check_comparison_list = check_json_file_data['features']
        check_comparison_list = [x.lower() for x in check_comparison_list]

        # Compare both lists and populate missing list
        missing_feature_count = 0
        for missing_feature in check_comparison_list:
            add_feature = False

            # Separate out features which contain a :
            if ":" in missing_feature:
                if not advanced_feature_match(missing_feature.lower(), main_comparison_list):
                    add_feature = True
            else:
                if not missing_feature.lower() in main_comparison_list:
                    add_feature = True

            if add_feature:
                missing_features.append(missing_feature.lower())
                missing_feature_count += 1

        if len(missing_features) == 0:
            log.info(f"[OK] There are no missing features found when comparing to file: {check_features_file}")
        else:
            log.info(f"{missing_feature_count} missing feature(s) found, when comparing to file: {check_features_file}")
            missing_features.sort()

        return missing_features

    except Exception as e:
        raise Exception(f"[ERROR] Failed to compare files. {e}")


def check_org_config_files(auto=False):
    """Checks the orgs/dev.json and orgs/dev_preview.json file for key settings

        Args:
            auto (bool): Optional parameter to set the checker to automatically update errors when they are found.

    """

    log.info("Scratch Org File Check: Checking your org config files for issues")
    error_found = False

    if not os.path.exists("orgs/dev.json"):
        raise Exception(f"The provided file path for the dev scratch org definition file, located at (orgs/dev.json), does not exist.")

    if not os.path.exists("orgs/dev_preview.json"):
        raise Exception(f"The provided file path for the dev scratch org definition file, located at (orgs/dev_preview.json), does not exist.")

    for scratch_config_file in ('orgs/dev.json', 'orgs/dev_preview.json'):
        # Check for "Enterprise" or "Partner Enterprise" edition in scratch org definition
        current_edition = get_json_file_value(scratch_config_file, "edition")

        if current_edition and "enterprise" not in current_edition.lower():
            log.info(f"Scratch Org File Check: [FAIL] Your {scratch_config_file} file is not set to Enterprise edition.")
            error_found = True
            if not auto:
                update_dev_input = input("\n\nWould you like to update the dev.json file edition? (y/n) Default y: ") or 'y'
            else:
                update_dev_input = 'y'
            if update_dev_input == 'y':
                update_json_file_value('orgs/dev.json', 'edition', 'Enterprise')
                log.info(f"Scratch Org File Check: Updated {scratch_config_file} to use Enterprise Edition")

    instance = get_json_file_value("orgs/dev_preview.json", "instance") or ""
    if "na135" not in instance.lower():
        log.error(
            "Scratch Org File Check: [FAIL] Your org/dev_preview.json file is not set to the NA135 Instance.")
        error_found = True
        if not auto:
            update_dev_input = input(
                "\n\nWould you like to update the dev_preview.json file instance? (y/n) Default y: ") or 'y'
        else:
            update_dev_input = 'y'
        if update_dev_input == 'y':
            update_json_file_value('orgs/dev_preview.json', 'instance', 'NA135')
            remove_json_entry('orgs/dev_preview.json', 'release')

    if not error_found:
        log.info("Scratch Org File Check: [OK] All files have passed checks")


def check_api_versions(project_api_version):
    """Checks API Versions within the project are all in sync with cumulusci.yml file api version

            Args:
                project_api_version (str): Current Project API version, defined in cumulusci.yml file.

    """

    log.info(f"API Version Check: Checking File API Versions are set to v{project_api_version}")

    # Check and Update sfdx-project.json File
    sfdx_version = get_json_file_value("sfdx-project.json", "sourceApiVersion")
    if project_api_version != sfdx_version:
        update_json_file_value("sfdx-project.json", "sourceApiVersion", project_api_version)
        log.info("API Version Check: Updated sfdx-project.json File")


def source_org_feature_checker(skip_rebuild=False, auto=False):
    """Check all source project dev.json files for missing features from current project dev.json file

        Args:
            skip_rebuild (bool): Skips the rebuild step. Typically only used for testing purposes.
            auto (bool): Optional parameter to set the checker to automatically update errors when they are found.
    """

    log.info("Source Feature Check: Checking that all source dev.json file features are listed in the current orgs/dev.json file")

    # Prepare Project File
    if not skip_rebuild:
        clean_project_files()
        rebuild_cci_cache()
    else:
        log.info("Cache Rebuild Skipped")

    # Locate all dev.json files in CCI Cache
    dev_files = glob.glob(".cci/projects" + "/**/dev.json", recursive=True)

    # Check for missing features and add them to dev.json
    main_missing_feature_list = []
    for feature_check_file in dev_files:
        missing_feature_list = find_missing_features("orgs/dev.json", feature_check_file)
        if missing_feature_list is not None and len(missing_feature_list) > 0:
            main_missing_feature_list.extend(missing_feature_list)
    if len(main_missing_feature_list) > 0:
        main_missing_feature_list.sort()
        update_org_file_features("orgs/dev.json", main_missing_feature_list, auto)
    else:
        log.info("Source Feature Check: No missing features found when comparing all sources to orgs/dev.json")


def org_feature_checker(auto=False):
    """ Checks and updates the dev_preview.json file with missing features from the dev.json file """

    log.info(
        "Scratch Org Config Check: Comparing dev.json and dev_preview.json files for missing features.")
    missing_features = find_missing_features("orgs/dev_preview.json", "orgs/dev.json")
    if len(missing_features) > 0:
        log.info("Scratch Org Config Check: Missing Features Found. Updating orgs/dev_preview.json file")
        update_org_file_features("orgs/dev_preview.json", missing_features, auto)
    else:
        log.info("Scratch Org Config Check: No Missing Features Found")


def check_for_missing_files():
    """ Checks for essential files within the current project folder """

    if not exists("cumulusci.yml"):
        log.error("[ERROR] Missing File: cumulusci.yml")
    if not exists("orgs/dev.json"):
        log.error("[ERROR] Missing File: orgs/dev.json")
    if not exists("sfdx-project.json"):
        log.error("[ERROR] Missing File: sfdx-project.json")
    if not exists("orgs/dev_preview.json"):
        log.error("[ERROR] Missing File: orgs/dev_preview.json")


def download_and_unzip(url: Optional[str] = DEFAULT_UPDATE_LOCATION, archive_password: Optional[str] = None, ignore_optional_updates: Optional[bool] = False, q_update: Optional[bool] = False) -> bool:
    """
    Downloads a .zip file and extracts all contents to the root project directory in the same structure they are within the zip file.

    Args:
        url (str): The URL where the .zip file is located. Note that this must be publicly accessible. If none is specified it will default to the QBrix Update Location
        archive_password (str): Optional password for the .zip file
        ignore_optional_updates (bool): Set to True to ignore anything flagged as optional. Applies only to the Q Brix Updates. Defaults to False
        q_update (bool): This is set to True to generate additional folders in the project directory when a Q Brix update is running. Defaults to False

    Returns:
        bool: Returns True when the process has completed and False if there has been an issue.

    """

    try:
        zipfile = ZipFile(BytesIO(urlopen(url).read()))

        # Set Password if given
        if archive_password:
            zipfile.setpassword(pwd=bytes(archive_password, 'utf-8'))

        # Set Extraction Path
        extract_path = "."

        # When Q Brix Update, Ensure all paths are created and clear old download
        if q_update:
            if not exists(".qbrix"):
                os.mkdir(".qbrix")

            if not exists(".qbrix/Update"):
                os.mkdir(".qbrix/Update")

            extract_path = ".qbrix/Update/"

            if exists(".qbrix/Update/xDO-Template-main"):
                shutil.rmtree(".qbrix/Update/xDO-Template-main")

        # Ensure Extract Paths
        dir_check_list = [x for x in zipfile.namelist() if x.endswith('/')]
        for d in dir_check_list:
            if not exists(extract_path + d):
                os.mkdir(extract_path + d)

        # Extract Files
        zipfile.extractall(path=extract_path)

        # Clean Up
        dirs = glob.glob(".qbrix/Update/**/__pycache__/", recursive=True)
        for folder in dirs:
            shutil.rmtree(folder)
        if exists("__MACOSX"):
            shutil.rmtree("__MACOSX")
        if exists("q_update_package"):
            shutil.rmtree("q_update_package")
        if ignore_optional_updates:
            if exists(".qbrix/OPTIONAL_UPDATES"):
                shutil.rmtree(".qbrix/OPTIONAL_UPDATES")

        return True
    except Exception as e:
        log.error(f"[ERROR] Update Failed! Error Message: {e}")
        if exists("q_update_package"):
            shutil.rmtree("q_update_package")
    return False


def check_and_update_old_class_refs():
    """
    Scans the cumulusci.yml file and ensures that any old class references have been updated to the new locations.
    """

    # Health Check
    replace_file_text("cumulusci.yml", "tasks.custom.qbrix_utils.HealthChecker", "qbrix.tools.utils.qbrix_health_check.HealthChecker")

    # Q Brix Update
    replace_file_text("cumulusci.yml", "tasks.custom.qbrix_utils.QBrixUpdater", "qbrix.tools.utils.qbrix_update.QBrixUpdater")

    # FART
    replace_file_text("cumulusci.yml", "tasks.custom.fart.FART", "qbrix.tools.utils.qbrix_fart.FART")

    # Batch Apex
    replace_file_text("cumulusci.yml", "tasks.custom.batchanonymousapex.BatchAnonymousApex", "qbrix.tools.utils.qbrix_batch_apex.BatchAnonymousApex")

    # Org Generator
    replace_file_text("cumulusci.yml", "tasks.custom.orggenerator.Spin", "qbrix.tools.utils.qbrix_org_generator.Spin")

    # Init Project
    replace_file_text("cumulusci.yml", "tasks.custom.qbrix_utils.Initialise_Project", "qbrix.tools.utils.qbrix_project_setup.InitProject")
    replace_file_text("cumulusci.yml", "tasks.custom.qbrix_utils.InitProject", "qbrix.tools.utils.qbrix_project_setup.InitProject")

    # List Q Brix
    replace_file_text("cumulusci.yml", "tasks.custom.qbrix_sf.ListQBrix", "qbrix.salesforce.qbrix_salesforce_tasks.ListQBrix")

    # Banner
    replace_file_text("cumulusci.yml", "tasks.custom.announce.CreateBanner", "qbrix.tools.shared.qbrix_console_utils.CreateBanner")

    # Mass File Ops
    replace_file_text("cumulusci.yml", "tasks.custom.qbrix_utils.MassFileOps", "qbrix.tools.utils.qbrix_mass_ops.MassFileOps")

    # SFDMU
    replace_file_text("cumulusci.yml", "tasks.custom.sfdmuload.SFDMULoad", "qbrix.tools.data.qbrix_sfdmu.SFDMULoad")

    # TESTIM
    replace_file_text("cumulusci.yml", "tasks.custom.testim.RunTestim", "qbrix.tools.testing.qbrix_testim.RunTestim")


def clean_project_files():
    """
    Removes known directories and files from a Q Brix Project folder which can be safely removed.
    """

    # Add Directory Paths to this list to have them removed by cleaner
    dirs_to_remove = [
        ".cci/projects",
        "src",
        "browser"
    ]

    # Add File Paths to this list to have them removed by cleaner
    files_to_remove = [
        "log.html",
        "playwright-log.txt",
        "output.xml",
        "report.html",
        "validationresult.json"
    ]

    if dirs_to_remove:
        for d in dirs_to_remove:
            check_and_delete_dir(d)

    if files_to_remove:
        for f in files_to_remove:
            check_and_delete_file(f)


def delete_standard_fields():
    """
    Removes Core/Standard Fields from Project Source. These are fields which are often pulled down when a standard Object is changed, like Account. Only custom fields need to be stored in the project, so this cleans up the other fields.
    """
    object_fields = glob.glob("force-app/main/default/objects/**/*.field-meta.xml", recursive=True)
    if object_fields and len(object_fields) > 0:
        for of in object_fields:
            if not os.path.basename(of).endswith("__c.field-meta.xml"):
                os.remove(of)


def update_file_api_versions(project_api_version) -> bool:
    """
    Scans specific files in the project which specify their own API version and updates them to be the same as the provided version

    Args:
        project_api_version: Target API Version you want to update the files to. e.g. 56

    Returns:
        bool: Returns True when complete. False if there was an issue.
    """

    if not project_api_version:
        return False

    # Init FART
    second_wind = FART()

    # File Locations To Check
    file_pattern_locations = [
        "force-app/main/default/classes/**/*.cls-meta.xml",
        "force-app/main/default/aura/**/*.cmp-meta.xml",
        "force-app/main/default/lwc/**/*.js-meta.xml",
        "files/package.xml",
        "sfdx-project.json"
    ]

    file_list = []
    if file_pattern_locations and len(file_pattern_locations) > 0:
        for pattern in file_pattern_locations:
            file_list += glob.glob(pattern, recursive=True)

        if len(file_list) > 0:
            for f in file_list:
                if not os.path.exists(f):
                    continue

                left_side = "<apiVersion>"
                right_side = "</apiVersion>"

                if f == "files/package.xml":
                    left_side = "<version>"
                    right_side = "</version>"
                elif f == "sfdx-project.json":
                    left_side = "<sourceApiVersion>"
                    right_side = "</sourceApiVersion>"

                second_wind.fartbetween(srcfile=f, left=left_side, right=right_side, replacewith=project_api_version, formatval=None)

    return True


def upsert_gitignore_entries(list_entries) -> bool:
    """
    Upserts a list of given gitignore patterns in the .gitignore file within the project. Each pattern is checked and if it is missing, it is added. If it exists but has been commented out, it will uncomment it.

    Args:
        list_entries (list(str)): List of strings which represent the gitignore patterns to check and upsert.

    Returns:
        bool: Returns True when completed, else False if there was an issue.
    """

    if len(list_entries) == 0:
        return False

    if not os.path.exists(".gitignore"):
        return False

    log.info("Checking .gitignore File")

    with open(".gitignore", 'a+') as git_file:
        git_file.seek(0)
        content = git_file.read()

        for entry in list_entries:
            if entry not in content or f"#{entry}" in content:
                git_file.write(f"{entry}\n")

    return True


def check_permset_group_files():
    """
    Checks Permission Set Group Metadata Files and ensures they are set as 'Outdated'. This ensures they are recalculated upon deployment to an org.
    """
    psg_files = glob.glob("force-app/main/default/permissionsetgroups/**/*.permissionsetgroup-meta.xml", recursive=True)
    if len(psg_files) > 0:
        log.info("Checking Permission Set Group File(s)")
        for psg in psg_files:
            log.info(f"Checking {psg} file configuration.")
            FART.fartbetween(FART, psg, "<status>", "</status>", "Outdated", None)


def add_prefix(path, prefix):
    parts = os.path.split(path)
    return os.path.join(parts[0], prefix + parts[1])


def update_references(old_value, new_value, prefix=''):
    """
    Walks through project folders and updates all references to a new prefixed reference

    Args:
        old_value (str): The previous reference string to search for
        new_value (str): The updated reference string to search for
        prefix (str): The prefix to add
    """

    if old_value == 'All':
        return

    if old_value == new_value:
        return

    project_path = 'force-app/main/default'
    reference_pattern = re.compile(rf'(?<!{prefix})\b{old_value}\b')

    for project_path in ["force-app/main/default", "unpackaged/pre", "unpackaged/post"]:
        for root, dirs, files in os.walk(project_path):
            for file_name in files:
                if "external_id" in os.path.basename(file_name).lower() or os.path.basename(file_name).lower().startswith("sdo_") or os.path.basename(file_name).lower().startswith("xdo_") or os.path.basename(file_name).lower().startswith("db_"):
                    continue

                if os.path.basename(root) in {"standardValueSets", "roles", "corsWhitelistOrigins"}:
                    continue

                file_path = os.path.join(root, file_name)
                with open(file_path, 'r', encoding='utf-8') as f:
                    f.seek(0)
                    file_contents = f.read()

                new_contents = reference_pattern.sub(new_value, file_contents)
                if new_contents != file_contents:
                    try:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_contents)
                            print(f'Updated references for {old_value} in {file_path}')
                    except Exception as e:
                        log.debug(e)
                        pass


def assign_prefix_to_files(prefix, parent_folder='force-app/main/default', interactive_mode=False):
    """
    Assigns a given prefix like 'FINS_' to custom items within the project folder.

    Args:
        prefix (str): The prefix you want to assign to items
        parent_folder (str): The relative path to the folder containing the project files. Defaults to force-app/main/default
        interactive_mode (bool): If True, this will ask the end user if a file should be updated or not.

    """

    # Validation
    if not prefix:
        raise Exception("Error: No prefix provided to the Mass Rename Tool. You must provide a prefix.")

    if not os.path.exists(parent_folder):
        raise Exception("Parent folder doesn't exist. Please correct the folder path and try again.")

    # Generate Prefix Variations
    prefix = prefix.replace("_", "")
    under_prefix = str(prefix).upper() + "_"
    open_prefix = str(prefix).upper() + " "

    # Set Matching Pattern for Cumstom API references
    PATTERN = re.compile(r'^.+$')
    FILE_PATTERN = re.compile(r'^.+.')

    paths_to_rename = []

    # Find and Update Custom Object Folder Names
    for root, dirs, files in os.walk(os.path.join(parent_folder, 'objects')):
        for dir_name in dirs:
            # no need to ask for standard object, or any sub folders (like fields, recordTypes folder) in each object folder
            if not dir_name.lower().endswith('__c'):
                log.debug(f"Ignoring {dir_name}")
                continue

            # no need to ask for anything comes from managed package
            if re.match(r'^[a-zA-Z]+__', dir_name):
                log.debug(f"Ignoring {dir_name}")
                continue

            if PATTERN.match(dir_name) and not dir_name.lower().startswith(prefix.lower()):
                old_path = os.path.join(root, dir_name)
                new_path = add_prefix(old_path, under_prefix)
                print(f'CUSTOM OBJECT DIRECTORY FOUND:\n    Current Path: {old_path}\n    Updated Path: {new_path}')
                approve_change = False
                if interactive_mode:
                    confirmation = input("Are you happy to make this change? (Y/n) : ") or 'y'
                    if confirmation.lower() == 'y':
                        approve_change = True
                    else:
                        approve_change = False
                else:
                    approve_change = True
                if approve_change:
                    paths_to_rename.append((old_path, new_path))
                    update_references(os.path.basename(old_path), os.path.basename(new_path), prefix)

        if root.endswith('compactLayouts') or root.endswith('recordTypes') or root.endswith('businessProcesses') or root.endswith('fields'):
            for file_name in files:
                if root.endswith('listViews') and "All.listView" in file_name:
                    continue

                if not file_name.lower().startswith(prefix.lower()) and not file_name.lower().startswith('sdo_') and not file_name.lower().startswith('xdo_'):
                    old_path = os.path.join(root, file_name)
                    if root.endswith('businessProcesses'):
                        new_path = add_prefix(old_path, open_prefix)
                    else:
                        new_path = add_prefix(old_path, under_prefix)
                    # os.rename(old_path, new_path)
                    print(f'CUSTOM OBJECT FILE FOUND:\n    Current Path: {old_path}\n    Updated Path: {new_path}')

                    old_value = os.path.splitext(os.path.basename(old_path))[0].split('.')[0]
                    new_value = os.path.splitext(os.path.basename(new_path))[0].split('.')[0]

                    approve_change = False
                    if interactive_mode:
                        confirmation = input("Are you happy to make this change? (Y/n) : ") or 'y'
                        if confirmation.lower() == 'y':
                            approve_change = True
                        else:
                            approve_change = False
                    else:
                        approve_change = True
                    if approve_change:
                        paths_to_rename.append((old_path, new_path))
                        update_references(old_value, new_value, prefix)

    # Update Custom File Names
    file_list = glob.glob(f'{parent_folder}/**/*.*-meta.xml', recursive=True)

    for current_file in file_list:
        file_name = os.path.basename(current_file)
        directory_name = os.path.dirname(current_file)

        if os.path.basename(directory_name) in {"settings", "standardValueSets", "roles", "corsWhitelistOrigins", "layouts", "quickActions"} or "objects" in directory_name:
            continue

        if "external_id" in file_name.lower() or file_name.lower().startswith("sdo_") or file_name.lower().startswith("xdo_") or file_name.lower().startswith(f"{prefix}") or file_name.lower().startswith("db_") or file_name.lower().startswith("standard-"):
            continue

        old_path = current_file
        new_path = add_prefix(old_path, under_prefix)
        print(f'PROJECT CUSTOM FILE FOUND:\n    Current Path: {old_path}\n    Updated Path: {new_path}')

        old_value = os.path.splitext(os.path.basename(old_path))[0].split('.')[0]
        new_value = os.path.splitext(os.path.basename(new_path))[0].split('.')[0]

        approve_change = False
        if interactive_mode:
            confirmation = input("Are you happy to make this change? (Y/n) : ") or 'y'
            if confirmation.lower() == 'y':
                approve_change = True
            else:
                approve_change = False
        else:
            approve_change = True
        if approve_change:
            paths_to_rename.append((old_path, new_path))
            update_references(old_value, new_value, prefix)

    # Rename all files and Folders where matches were located
    sorted_list = sorted(paths_to_rename, key=lambda x: len(x[1]), reverse=True)
    for path_to_update, new_updated_path in sorted_list:
        os.rename(path_to_update, new_updated_path)
        print(f"FILE OR FOLDER RENAMED:\n    Previous Path: {path_to_update}\n    New Path: {new_updated_path}")


def create_external_id_field(file_path: str = None):
    """
    Creates External ID Fields for a given list of Object Names. If no file is provided, this will generate External ID fields on all objects within the current project directory.

    Args:
        file_path (str): Relative Path within Project to a .txt file containing a list of objects to process. If not provided, will generate a list of objects from the current project.
    """

    object_list = []

    if file_path:
        with open(file_path) as file:
            for line in file:
                if line and len(line) > 1:
                    object_list.append(line.strip())
    else:
        for obj in os.listdir("force-app/main/default/objects"):
            object_list.append(obj)

    if len(object_list) > 0:
        for project_object in object_list:
            if project_object:
                object_dir = os.path.join("force-app", "main", "default", "objects", project_object)
                fields_dir = os.path.join(object_dir, "fields")
                field_file = os.path.join(fields_dir, "External_ID__c.field-meta.xml")
                if not os.path.exists(object_dir):
                    os.makedirs(object_dir)
                if not os.path.exists(fields_dir):
                    os.makedirs(fields_dir)
                if not os.path.exists(field_file):
                    with open(field_file, "w") as f:
                        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                        f.write('<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">\n')
                        f.write('    <fullName>External_ID__c</fullName>\n')
                        f.write('    <externalId>true</externalId>\n')
                        f.write('    <label>External ID</label>\n')
                        f.write('    <length>50</length>\n')
                        f.write('    <required>false</required>\n')
                        f.write('    <trackTrending>false</trackTrending>\n')
                        f.write('    <type>Text</type>\n')
                        f.write('    <unique>false</unique>\n')
                        f.write('</CustomField>\n')


def run_command(command, cwd="."):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True, cwd=cwd)
    output, error = process.communicate()

    if error:
        raise Exception(error)
    return output, error


def compare_directories(dcmp):
    new_or_changed = []
    for name in dcmp.right_only:
        new_or_changed.append(os.path.join(dcmp.right, name))
    for name in dcmp.diff_files:
        new_or_changed.append(os.path.join(dcmp.right, name))
    for sub_dcmp in dcmp.subdirs.values():
        new_or_changed.extend(compare_directories(sub_dcmp))
    return new_or_changed


def compare_metadata(target_org_alias):
    # Default Org Command
    if os.path.exists('src'):
        shutil.rmtree('src')

    if os.path.exists('mdapipkg'):
        shutil.rmtree('mdapipkg')

    if os.path.exists('upgrade_src'):
        shutil.rmtree('upgrade_src')

    run_command("cci task run dx_convert_from")

    # Retrieve metadata from the target org
    log.info(f"Retrieving metadata from the target org with alias {target_org_alias} (This can take a few minutes..)")
    retrieve_command = f"cci task run dx --command \"force:mdapi:retrieve -r mdapipkg -k src/package.xml\" --org {target_org_alias}"
    run_command(retrieve_command)

    # Unzip the retrieved metadata
    log.info("Unpacking Metadata")
    unzip_command = f"unzip -o mdapipkg/unpackaged.zip -d mdapipkg/unpackaged"
    run_command(unzip_command)

    # Compare the local and target org's metadata
    log.info("Comparing Metadata")
    dcmp = filecmp.dircmp('mdapipkg/unpackaged/unpackaged', 'src')
    new_or_changed = compare_directories(dcmp)

    changes = []

    if len(new_or_changed) > 0:
        log.info(f"{len(new_or_changed)} changes found")
        log.info("Generating new update package in directory: upgrade_src")

        for file_path in new_or_changed:
            if os.path.basename(os.path.dirname(file_path)) in {'settings', 'labels'}:
                log.info(f"Skipping {file_path} as it contains a high risk metadata type. Review the contents individually.")
                continue

            changes.append(file_path)

            # Determine the destination path of the metadata file to copy
            dst_file_path = os.path.join('upgrade_src', file_path.replace('src/', ''))

            # Create the destination directory if it does not exist
            dst_directory = os.path.dirname(dst_file_path)
            if not os.path.exists(dst_directory):
                os.makedirs(dst_directory)

            # Copy the metadata file to the destination directory
            shutil.copy2(file_path, dst_file_path)

        run_command("sfdx force:source:manifest:create --sourcepath upgrade_src --manifestname upgrade_src/package")

    return changes


def push_changes(target_org_alias):
    # Push Changes
    push_command = f"cci task run deploy --path upgrade_src --org {target_org_alias}"
    push_output, push_error = run_command(push_command)

    log.info("Upgrade Pushed!")
    return push_output


def create_permission_set_file(name, label):
    """
    Creates a Permission Set from the current Project.

    Args:
        name (str): The Name for the Permission Set File
        label (str): The label for the Permission Set
    """

    if os.path.exists(f"force-app/main/default/permissionsets/{name}.permissionset-meta.xml"):
        os.remove(f"force-app/main/default/permissionsets/{name}.permissionset-meta.xml")

    # Adjust long labels to the max length
    if len(label) > 80:
        log.info("Adjusted label length as you have passed in a permission set label name which is more than 80 characters.")
        label = label[:80]

    # Create the root element
    root = ET.Element("PermissionSet", attrib={"xmlns": "http://soap.sforce.com/2006/04/metadata"})

    # Set the label
    label_element = ET.SubElement(root, "label")
    label_element.text = label

    # NOTE FOR DEVS - The Traversal of objects and fields needs to ensure that the resulting tree has all types grouped together, i.e. all object references, all fields references then all record types. Hence the strange order of execution below.

    # Traverse through the object folders
    object_lookup_list = []
    objects_path = "force-app/main/default/objects"
    if os.path.exists(objects_path):
        for object_folder in os.listdir(objects_path):
            object_folder_path = os.path.join(objects_path, object_folder)
            if os.path.isdir(object_folder_path):
                # Add object permissions
                object_permissions_element = ET.SubElement(root, "objectPermissions")
                ET.SubElement(object_permissions_element, "allowCreate").text = "true"
                ET.SubElement(object_permissions_element, "allowDelete").text = "true"
                ET.SubElement(object_permissions_element, "allowEdit").text = "true"
                ET.SubElement(object_permissions_element, "allowRead").text = "true"
                ET.SubElement(object_permissions_element, "modifyAllRecords").text = "true"
                ET.SubElement(object_permissions_element, "object").text = f"{object_folder}"
                ET.SubElement(object_permissions_element, "viewAllRecords").text = "true"

                # Traverse through the field folders
                fields_folder_path = os.path.join(object_folder_path, "fields")
                if os.path.isdir(fields_folder_path):
                    for field_file in os.listdir(fields_folder_path):
                        # # Add object permissions for lookup fields that reference objects not in the project
                        field_path = os.path.join(fields_folder_path, field_file)
                        with open(field_path, "r") as file:
                            contents = file.read()
                            reference_to_start = contents.find("<referenceTo>")
                            reference_to_end = contents.find("</referenceTo>")
                            if reference_to_start != -1 and reference_to_end != -1:
                                reference_object = contents[reference_to_start + 13:reference_to_end]
                                if reference_object not in os.listdir(objects_path) and reference_object not in object_lookup_list:
                                    object_permissions_element = ET.SubElement(root, "objectPermissions")
                                    ET.SubElement(object_permissions_element, "allowCreate").text = "true"
                                    ET.SubElement(object_permissions_element, "allowDelete").text = "true"
                                    ET.SubElement(object_permissions_element, "allowEdit").text = "true"
                                    ET.SubElement(object_permissions_element, "allowRead").text = "true"
                                    ET.SubElement(object_permissions_element, "modifyAllRecords").text = "true"
                                    ET.SubElement(object_permissions_element, "object").text = f"{reference_object}"
                                    ET.SubElement(object_permissions_element, "viewAllRecords").text = "true"
                                    object_lookup_list.append(reference_object)

    # Traverse Field Names
    if os.path.exists(objects_path):
        for object_folder in os.listdir(objects_path):
            object_folder_path = os.path.join(objects_path, object_folder)
            if os.path.isdir(object_folder_path):
                # Traverse through the field folders
                fields_folder_path = os.path.join(object_folder_path, "fields")
                if os.path.isdir(fields_folder_path):
                    for field_file in os.listdir(fields_folder_path):
                        # Read File and skip MasterDetail and Formula Fields
                        with open(os.path.join(fields_folder_path, field_file), "r") as file:
                            contents = file.read()
                            formula_reference_to_start = contents.find("<formula>")
                            md_reference_to_start = contents.find("<type>MasterDetail</type>")
                            req_reference_to_start = contents.find("<required>true</required>")
                        # Add Field to the tree
                        if field_file.endswith(".field-meta.xml") and formula_reference_to_start == -1 and md_reference_to_start == -1 and req_reference_to_start == -1:
                            field_name = field_file[:-15]
                            field_permissions_element = ET.SubElement(root, "fieldPermissions")
                            ET.SubElement(field_permissions_element, "editable").text = "true"
                            ET.SubElement(field_permissions_element, "field").text = f"{object_folder}.{field_name}"
                            ET.SubElement(field_permissions_element, "readable").text = "true"

    # Traverse Record Types
    if os.path.exists(objects_path):
        for object_folder in os.listdir(objects_path):
            object_folder_path = os.path.join(objects_path, object_folder)
            if os.path.isdir(object_folder_path):
                record_types_folder_path = os.path.join(object_folder_path, "recordTypes")
                if os.path.isdir(record_types_folder_path):
                    for record_type_file in os.listdir(record_types_folder_path):
                        if record_type_file.endswith(".recordType-meta.xml"):
                            record_type_name = record_type_file[:-20]
                            record_type_permissions_element = ET.SubElement(root, "recordTypeVisibilities")
                            ET.SubElement(record_type_permissions_element, "recordType").text = f"{object_folder}.{record_type_name}"
                            ET.SubElement(record_type_permissions_element, "visible").text = "true"

    # Traverse through the Apex class files
    classes_path = "force-app/main/default/classes"
    if os.path.exists(classes_path):
        for class_file in os.listdir(classes_path):
            if class_file.endswith(".cls"):
                class_name = class_file[:-4]
                class_permissions_element = ET.SubElement(root, "classAccesses")
                ET.SubElement(class_permissions_element, "apexClass").text = f"{class_name}"
                ET.SubElement(class_permissions_element, "enabled").text = "true"

    # Traverse through the tab files
    tabs_path = "force-app/main/default/tabs"
    if os.path.exists(tabs_path):
        for tab_file in os.listdir(tabs_path):
            if tab_file.endswith(".tab-meta.xml"):
                tab_name = tab_file[:-13]
                tab_permissions_element = ET.SubElement(root, "tabSettings")
                ET.SubElement(tab_permissions_element, "tab").text = f"{tab_name}"
                ET.SubElement(tab_permissions_element, "visibility").text = "Visible"

    # Traverse through the Application files
    apps_path = "force-app/main/default/applications"
    if os.path.exists(apps_path):
        for apps_file in os.listdir(apps_path):
            if apps_file.endswith(".app-meta.xml"):
                app_name = apps_file[:-13]
                app_permissions_element = ET.SubElement(root, "applicationVisibilities")
                ET.SubElement(app_permissions_element, "application").text = f"{app_name}"
                ET.SubElement(app_permissions_element, "visible").text = "true"

    # Create the file
    if not os.path.exists("force-app/main/default/permissionsets"):
        os.makedirs("force-app/main/default/permissionsets")

    file_path = f"force-app/main/default/permissionsets/{name}.permissionset-meta.xml"
    with open(file_path, "w", encoding="utf-8") as file:
        xml_string = ET.tostring(root, encoding="unicode")
        xml_dom = minidom.parseString(xml_string)
        formatted_xml = xml_dom.toprettyxml(indent="  ", encoding="utf-8")
        file.write(formatted_xml.decode("utf-8"))

def get_packages_in_stack(skip_cache_rebuild=False, whole_stack=True):

    """
    Finds all package references within the current stack or locally within the current project.
    """

    package_list = []

    # Regenerate cci cache
    if not skip_cache_rebuild:
        rebuild_cci_cache()

    if whole_stack:
        qbrix_dirs = sorted(os.listdir(".cci/projects"))
        for qbrix in qbrix_dirs:
            cci_yml = glob.glob(f"{os.path.join('.cci', 'projects', qbrix)}/**/cumulusci.yml", recursive=True)
            if len(cci_yml) > 0:
                with open(cci_yml[0], 'r') as f:
                    config = yaml.safe_load(f)
                
                dependencies = config['project'].get("dependencies")
                if dependencies:
                    for d in dependencies:
                        if d.get("version_id"):
                            package_list.append((d.get("version_id"), qbrix))

    with open('cumulusci.yml', 'r') as f:
        local_config = yaml.safe_load(f)
            
        local_dependencies = local_config['project'].get("dependencies")
        if local_dependencies:
            for d in local_dependencies:
                if d.get("version_id"):
                    package_list.append((d.get("version_id"), 'LOCAL'))

    return package_list


def generate_stack_view(parent_directory_path='.cci/projects', output="terminal"):
    # Regenerate cci cache
    rebuild_cci_cache()

    if not os.path.exists('.cci/projects'):
        print("No Sources to traverse. Skipping")
        return

    # Get Stack folder locations and order
    sub_directory_names_sorted = sorted(os.listdir(parent_directory_path))
    sub_directory_names_sorted.append("LOCAL")

    files_list = []
    overwritten_files_list = []

    if output == "terminal":
        print("Sending outputs to the Terminal")
        print("\n***SOURCE QBRIX FILES***")
    else:
        now = datetime.datetime.now()
        log_file_name = "stack_log_" + now.strftime("%Y%m%d%H%M%S") + ".txt"
        log_file = open(log_file_name, "w")
        print(f"Sending output to log file, located at {log_file_name}")
        log_file.write("\n***SOURCE QBRIX FILES***")

    for i, qbrix in enumerate(sub_directory_names_sorted):
        if qbrix != "LOCAL":
            if output == "terminal":
                print(f"\n{qbrix}")
                print("-" * len(qbrix))
            else:
                log_file.write(f"\n\n{qbrix}\n")
                log_file.write("-" * len(qbrix))

            cci_yml = glob.glob(f"{os.path.join('.cci', 'projects', qbrix)}/**/cumulusci.yml", recursive=True)

            if cci_yml:
                with open(cci_yml[0], 'r') as f:
                    config = yaml.safe_load(f)

                api_version = config['project']['package']['api_version']
                if api_version:
                    if output == "terminal":
                        print(f"\nAPI Version: {api_version}")
                    else:
                        log_file.write(f"\nAPI Version: {api_version}")
                else:
                    if output == "terminal":
                        print("\nAPI Version: ERROR MISSING!!!")
                    else:
                        log_file.write("\nAPI Version: ERROR MISSING!!!")

                repo_url = config['project']['git']['repo_url']
                if repo_url:
                    if output == "terminal":
                        print(f"\nREPO URL: {repo_url}")
                    else:
                        log_file.write(f"\nREPO URL: {repo_url}")
                else:
                    print("\nREPO URL: ERROR MISSING!!!")

                dependencies = config['project'].get("dependencies")
                if dependencies and len(dependencies) > 0:
                    if output == "terminal":
                        print("\nPACKAGES:")
                    else:
                        log_file.write("\nPACKAGES:")

                    for d in dependencies:
                        if d.get("namespace"):
                            if output == "terminal":
                                print(f" - Managed Package: {d.get('namespace')}")
                            else:
                                log_file.write(f"\n - Managed Package: {d.get('namespace')}")
                        if d.get("version_id"):
                            if output == "terminal":
                                print(f" - Unmanaged Package Version ID: {d.get('version_id')}")
                            else:
                                log_file.write(f"\n - Unmanaged Package Version ID: {d.get('version_id')}")
                        if d.get("github"):
                            if output == "terminal":
                                print(f" - Github Repo: {d.get('github')}")
                            else:
                                log_file.write(f"\n - Github Repo: {d.get('github')}")
            if output == "terminal":
                print("\nFILES:")
            else:
                log_file.write(f"\nFILES:")
            for root, dirs, files in os.walk(os.path.join(".cci", "projects", qbrix)):
                if "force-app/main/default" in root:
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        force_app_index = file_path.find("force-app/main/default/")
                        if force_app_index != -1:
                            file_path = os.path.join(file_path[force_app_index + len("force-app/main/default/"):])
                            if output == "terminal":
                                print(f" - {file_path}")
                            else:
                                log_file.write(f"\n - {file_path}")
                            if i == 0:
                                files_list.append((file_path, qbrix))
                            else:
                                if len([t for t in files_list if t[0] == file_path]) >= 1:
                                    overwritten_files_list.append((file_path, qbrix))
                                else:
                                    files_list.append((file_path, qbrix))

        else:
            if output == "terminal":
                print(f"\nLOCAL QBRIX")
                print("-" * len("LOCAL QBRIX"))
            else:
                log_file.write(f"\n\nLOCAL QBRIX\n")
                log_file.write("-" * len("LOCAL QBRIX"))

            for root, dirs, files in os.walk("force-app/main/default"):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    force_app_index = file_path.find("force-app/main/default/")
                    if force_app_index != -1:
                        file_path = os.path.join(file_path[force_app_index + len("force-app/main/default/"):])
                        if output == "terminal":
                            print(f" - {file_path}")
                        else:
                            log_file.write(f"\n - {file_path}")
                        if i == 0:
                            files_list.append((file_path, qbrix))
                        else:
                            if len([t for t in files_list if t[0] == file_path]) >= 1:
                                overwritten_files_list.append((file_path, qbrix))
                            else:
                                files_list.append((file_path, qbrix))

    if output == "terminal":
        print("\n***STACK FILES WHICH ARE REDEPLOYED***")
    else:
        log_file.write("\n\n***STACK FILES WHICH ARE REDEPLOYED***")

    for f, q in files_list:
        overwrite_matches = [t for t in overwritten_files_list if t[0] == f]

        if len(overwrite_matches) > 0:
            if output == "terminal":
                print(f"\n{f} (Deployed By {q})")
            else:
                log_file.write(f"\n\n{f} (Deployed By {q})")

            for o in list(set(overwrite_matches)):
                if o[1] != q:
                    if output == "terminal":
                        print(f" > Updated in: {o[1]}")
                    else:
                        log_file.write(f"\n > Updated in: {o[1]}")
    if output == "terminal":
        print("\n***STACK STATS***")
        print(f"\nTotal Files in Stack: {len(files_list)}")
        print(f"Total Files updated within stack: {len(overwritten_files_list)}")
    else:
        log_file.write(f"\n***STACK STATS***\n\nTotal Files in Stack: {len(files_list)}\nTotal Files updated within stack: {len(overwritten_files_list)}")

    if output != "terminal":
        log_file.close()

def remove_empty_translations():
    
    """
    Removes empty translations from the project directory. Defaults to the force-app/main/default/objectTranslations directory.
    """

    # Define the path to the objectTranslations directory
    obj_trans_dir = os.path.join('force-app', 'main', 'default', 'objectTranslations')
    
    # Loop through all subdirectories in the objectTranslations directory
    for obj_dir in os.listdir(obj_trans_dir):
        obj_dir_path = os.path.join(obj_trans_dir, obj_dir)
        if not os.path.isdir(obj_dir_path):
            continue
        
        # Check if all label tags have no value
        
        for trans_file in os.listdir(obj_dir_path):
            if not trans_file.endswith('.xml'):
                continue
            
            trans_file_path = os.path.join(obj_dir_path, trans_file)
            tree = ET.parse(trans_file_path)
            root = tree.getroot()
            has_translation = False
            for child in root:
                if child.find('label') is not None and child.find('label').text != '':
                    has_translation = True
                    break
            
            if not has_translation:
                print(f"No translation found in {trans_file_path}")
                os.remove(trans_file_path)
                remove_obj_dir = True
            else:
                remove_obj_dir = False
        
        # Remove object directory if all files within have no translations
        if remove_obj_dir:
            os.rmdir(obj_dir_path)

    # Remove objectTranslations directory if empty
    if not os.listdir(obj_trans_dir):
        os.rmdir(obj_trans_dir)

def pretty_print(elem, level=0):
    indent = '    ' * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = '\n' + indent + '    '
        if not elem.tail or not elem.tail.strip():
            elem.tail = '\n' + indent
        for elem in elem:
            pretty_print(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = '\n' + indent
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = '\n' + indent

def check_and_update_setting(xml_file, settings_name, setting_name, setting_value):
    # Ensure the directories exist
    os.makedirs(os.path.dirname(xml_file), exist_ok=True)

    namespace = "http://soap.sforce.com/2006/04/metadata"
    nsmap = {'ns': namespace}

    if not os.path.isfile(xml_file):
        # File doesn't exist, create a new one with the settings element as the root
        root = ET.Element(settings_name)
        root.set("xmlns", namespace)
    else:
        # Parse the existing XML file
        ET.register_namespace('', namespace)
        tree = ET.parse(xml_file)
        root = tree.getroot()

    # Find the settings element
    setting_element = root.find('.//ns:'+setting_name, namespaces=nsmap)
    if setting_element is None:
        setting_element = ET.SubElement(root, setting_name)
        setting_element.text = str(setting_value)
    elif setting_element.text != str(setting_value):
        setting_element.text = str(setting_value)

    # Write the modified XML back to the file with formatting
    pretty_print(root)
    # Add XML declaration manually
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
    with open(xml_file, "w", encoding="utf-8") as file:
        file.write(xml_content)