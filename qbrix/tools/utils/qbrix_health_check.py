from abc import ABC
from qbrix.tools.shared.qbrix_console_utils import init_logger
from qbrix.tools.shared.qbrix_project_tasks import clean_project_files, check_api_versions, check_permset_group_files, check_and_update_old_class_refs, create_external_id_field, create_permission_set_file, delete_standard_fields, remove_empty_translations, source_org_feature_checker, org_feature_checker, check_org_config_files, update_file_api_versions, upsert_gitignore_entries, replace_file_text, get_qbrix_repo_url
from cumulusci.core.tasks import BaseTask
from qbrix.tools.shared.qbrix_json_tasks import update_json_file_value, get_json_file_value

log = init_logger()


class HealthChecker(BaseTask, ABC):
    task_options = {
        "auto": {
            "description": "Auto Accepts all proposed changes. Defaults to True",
            "required": False
        },
        "api_checker_include_code_files": {
            "description": "When True, updates code files within project to the project API version",
            "required": False
        },
        "remove_standard_fields": {
            "description": "When True, this removes all standard fields which have been pulled to source. Defaults to False",
            "required": False
        },
        "remove_empty_translations": {
            "description": "When True, removes empty translations from the project. Defaults to False",
            "required": False
        },
        "auto_generate_external_id_fields": {
            "description": "When True, reviews all objects within the project and generates an External_ID__c custom field, where there is not currently one. Defaults to False",
            "required": False
        },
        "regenerate_permission_set": {
            "description": "When True, this generates a permission set file for the project qbrix with the project name. Defaults to False",
            "required": False
        },
    }

    task_docs = """
    Checks for known configuration issues within the project files and corrects them (if possible). For anything that cannot be automatically repaired, the end user will be prompted for an action or simply shown a detailed error message with guidance on how to resolve the issue. Note that some errors come from outside of Q Brix and may not have additional guidance.
    """

    def _init_options(self, kwargs):
        super(HealthChecker, self)._init_options(kwargs)
        self.auto = self.options["auto"] if "auto" in self.options else True
        self.api_checker_include_code_files = self.options["api_checker_include_code_files"] if "api_checker_include_code_files" in self.options else False
        self.remove_standard_fields = self.options["remove_standard_fields"] if "remove_standard_fields" in self.options else False
        self.remove_empty_translations = self.options["remove_empty_translations"] if "remove_empty_translations" in self.options else False
        self.auto_generate_external_id_fields = self.options["auto_generate_external_id_fields"] if "auto_generate_external_id_fields" in self.options else False
        self.regenerate_permission_set = self.options["regenerate_permission_set"] if "regenerate_permission_set" in self.options else False

    def _run_task(self):
        self.logger.info("\nHealth Check: Starting Health Checker Tool")

        self.logger.info("\nHealth Check: Removing cached/unneeded files and folders from project.")
        clean_project_files()
        self.logger.info(" -> Check Complete!")

        self.logger.info("\nHealth Check: Checking for old class references and updating them...")
        check_and_update_old_class_refs()
        self.logger.info(" -> Check Complete!")

        self.logger.info("\nHealth Check: Checking placeholder names have been replaced and other naming is correct.")
        self.check_project_file_naming()
        self.logger.info(" -> Check Complete!")

        self.logger.info("\nHealth Check: Checking that all references to the API version, match the project version.")
        check_api_versions(self.project_config.project__package__api_version)
        if self.api_checker_include_code_files:
            update_file_api_versions(self.project_config.project__package__api_version)
        self.logger.info(" -> Check Complete!")

        self.logger.info("\nHealth Check: Checking that orgs/dev.json has all features from all sources related to this Q Brix.")
        source_org_feature_checker(False, self.auto)
        self.logger.info(" -> Check Complete!")

        self.logger.info("\nHealth Check: Checking that dev_preview has all features from dev.")
        org_feature_checker(self.auto)
        self.logger.info(" -> Check Complete!")

        self.logger.info("\nHealth Check: Checking that scratch org files are configured with required settings")
        check_org_config_files(True)
        self.logger.info(" -> Check Complete!")

        if self.remove_standard_fields:
            self.logger.info("\nHealth Check: Checking for standard object fields and removing them from the project")
            delete_standard_fields()
            self.logger.info(" -> Check Complete!")

        if self.remove_empty_translations:
            self.logger.info("\nHealth Check: Checking for and removing empty translations")
            remove_empty_translations()
            self.logger.info(" -> Check Complete!")

        if self.auto_generate_external_id_fields:
            self.logger.info("\nHealth Check: Checking for and adding External ID Fields to objects")
            create_external_id_field()
            self.logger.info(" -> Check Complete!")

        if self.regenerate_permission_set:
            project_name = self.project_config.project__name
            if project_name:
                self.logger.info("\nHealth Check: Checking and generating Permission Set for the Q Brix")
                permission_set_file_name = project_name.replace(" ", "_")
                permission_set_check = input(f"Please confirm that you understand that this will overwrite any existing file located at force-app/main/default/permissionsets/{permission_set_file_name}.permissionset-meta.xml: (y/n)")
                if permission_set_check and permission_set_check.lower() == 'y':
                    create_permission_set_file(permission_set_file_name, f"{project_name} Permission Set")
                    self.logger.info(" -> Check Complete!")
                else:
                    self.logger.info("Confirmation was not received, skipping Permission Set check and rebuild.")

        self.logger.info("\nHealth Check: Checking .gitignore file")
        test_list = []

        # ADD ENTRIES FOR THE .GITIGNORE FILE BELOW. LEFT THIS AS IS TO MAKE IT EASIER TO READ
        test_list.append(".sf/")
        test_list.append(".qbrix/")
        test_list.append("testim-headless.zip")
        test_list.append("src/")
        test_list.append(".cci/")
        test_list.append(".sfdx/")
        test_list.append("browser/")
        test_list.append("playwright-log.txt")
        test_list.append("log.html")
        test_list.append("output.xml")
        test_list.append("report.html")
        test_list.append(".qbrix/*")
        test_list.append("qbrix/robot/__pycache__")
        test_list.append("qbrix/salesforce/__pycache__")
        test_list.append("qbrix/tools/utils/__pycache__")
        test_list.append("qbrix/tools/shared/__pycache__")
        test_list.append("qbrix/tools/data/__pycache__")
        test_list.append("qbrix/tools/testing/__pycache__")
        test_list.append("tasks/custom/__pycache__")
        test_list.append("validationresult.json")
        test_list.append("*_results.xml")

        upsert_gitignore_entries(test_list)

        # Check to ensure that .vscode is not ignored from git
        replace_file_text(".gitignore", ".vscode/", "")

        # Check Permission Set Group Files are set to Outdated
        check_permset_group_files()

        self.logger.info(" -> Check Complete!")

        self.logger.info("\n\nHealth Check: All Checks completed!")

    def check_project_file_naming(self):

        """ Checks that the project file names are set correctly """

        repo_url = get_qbrix_repo_url()
        if repo_url is not None:
            repo_qbrix_name = repo_url.rsplit('/', 1)[-1]
        else:
            repo_qbrix_name = self.project_config.project__git__repo_url.rsplit('/', 1)[-1]

        project_name = self.project_config.project__name
        package_name = self.project_config.project__package__name
        repo_url = self.project_config.project__git__repo_url

        self.logger.info("Naming Check: Checking File and Project Naming aligns with correct Q Brix Name")
        file_name_error = False

        if project_name is None or package_name is None or repo_url is None:
            file_name_error = True
            log.error(
                "Naming Check: [FAIL] One or more of the required parameters are missing from the cumulusci.yml file. Check that the Project name, Project Package Name and Repo URL have all been added and populated.")
            self.logger.info(
                f"Names Found:\nProject Name: {project_name}\nPackage Name: {package_name}\nRepo URL: {repo_url}\nQBrix Name (From Repo URL): {repo_qbrix_name}")

        else:

            # Check Repo Name has been found
            if repo_qbrix_name is None:
                file_name_error = True
                log.error(
                    "Naming Check: [FAIL] Check you have a valid URL for the project > Repo Url in the cumulusci.yml file")
                self.logger.info(
                    f"Names Found:\nProject Name: {project_name}\nPackage Name: {package_name}\nRepo URL: {repo_url}\nQBrix Name (From Repo URL): {repo_qbrix_name}")

            # Check for the Template name in the config file.
            if 'xDO-Template' in project_name or 'xDO-Template' in package_name or 'xDO-Template' in repo_url:
                file_name_error = True
                log.error(
                    "Naming Check: [FAIL] You must update your project names in the cumulusci.yml file to be the same as your Q Brix repo url. xDO-Template was found and this should have been updated, see Readme.")
                self.logger.info(
                    f"Names Found:\nProject Name: {project_name}\nPackage Name: {package_name}\nRepo URL: {repo_url}\nQBrix Name (From Repo URL): {repo_qbrix_name}")

            # Check that the repo name and project names all match
            if not project_name == package_name == repo_qbrix_name:
                file_name_error = True
                log.error(
                    "Naming Check: [FAIL] You must update your project names in the cumulusci.yml file to be the same as your Q Brix repo url")
                self.logger.info(
                    f"Names Found:\nProject Name: {project_name}\nPackage Name: {package_name}\nRepo URL: {repo_url}\nQBrix Name (From Repo URL): {repo_qbrix_name}")

            # Check that the dev.json file has the correct qbrix name
            if repo_qbrix_name not in get_json_file_value("orgs/dev.json", "orgName"):
                log.debug("Naming Check: Updating OrgName in orgs/dev.json has not been updated. Updating now...")
                update_json_file_value("orgs/dev.json", "orgName", f"{repo_qbrix_name} - Dev org")
                self.logger.info("Naming Check: Updated orgs/dev.json")

            # Check that the dev_preview.json file has the correct qbrix name
            if repo_qbrix_name not in get_json_file_value("orgs/dev_preview.json", "orgName"):
                log.debug(
                    "Naming Check: Updating OrgName in orgs/dev_preview.json has not been updated. Updating Now...")
                update_json_file_value("orgs/dev_preview.json", "orgName", f"{repo_qbrix_name} - Preview Dev org")
                log.debug(
                    "Naming Check: Updated orgs/dev_preview.json")

        if not file_name_error:
            self.logger.info("Health Check: [OK] All naming Checks Passed!")
        else:
            self.logger.info(
                "Health Check: [ACTION NEEDED] Some tests did not pass. Check the error messages above for more information.")

        self.logger.info("Health Check: Naming Checks completed")
