from abc import ABC
import os
import shutil

from cumulusci.core.tasks import BaseTask
from cumulusci.core.config import ScratchOrgConfig, TaskConfig
from qbrix.salesforce.qbrix_salesforce_tasks import ComparePackages
from qbrix.tools.bundled.sam.main import migrate
from qbrix.tools.shared.qbrix_project_tasks import check_and_update_setting, generate_stack_view, update_file_api_versions, create_permission_set_file, push_changes, compare_metadata, delete_standard_fields, assign_prefix_to_files, create_external_id_field


class MassFileOps(BaseTask, ABC):
    task_docs = """
    Q Brix Mass Operations Utility has a number of helpful methods to save time when developing projects which store Salesforce metadata.
    """

    task_options = {}

    def _init_options(self, kwargs):
        super(MassFileOps, self)._init_options(kwargs)

    def _run_task(self):
        self.logger.info(f""" 
        \nQ BRIX - MASS OPERATIONS UTILITY\n\n
        OPTION  DESCRIPTION\n
        [1]     Update File APIs : Updates Apex Classes and LWC/Aura Components with Q Brix API Version\n
        [2]     Delete Standard Fields : Removes standard fields within object folders\n
        [3]     Prefix Generator : Assign Prefix to all Custom Entities (Folders and References) in Project\n
        [4]     External ID Field Generator : Generate External ID Fields for a list of Object names\n
        [5]     Push Upgrade Tool (BETA) : Compare changes in metadata between the target org and your project, then push changes to the org.\n
        [6]     Permission Set Generator : Generate Permission Set for Objects, Fields, Tabs and Classes in your project.\n
        [7]     Q Brix Stack Viewer (BETA): Generates a view of the metadata deployed by the whole stack of Q Brix.\n
        [8]     SAM CRM Analytics Migration Tool (v0.4.1 - BETA): Can be used to migrate CRMA Assets from one Salesforce Org to Another\n
        [e]     Exit   
    """)

        # Process Menu Selection
        option = input("\n\nWhich task you like to run? (Enter the option number) : ")
        if option.lower() == "1":
            # Update File APIs
            self.logger.info("***RUNNING UPDATE FILES API UTILITY***\n")

            confirmation = input("This will update ALL Apex Classes, Aura Component's and LWC Component's metadata files with the project API Version. Are you sure you want to continue? (y/n) Default y:") or 'y'
            if confirmation.lower() == 'y':
                project_api_version = self.project_config.project__package__api_version

                if not project_api_version:
                    self.logger.info("Error: Unable to read project API Version. Check your cumulusci.yml file.")
                    return

                self.logger.info(f"\nConfirmation Confirmed! Starting project file API update, checking for version {project_api_version}")
                if update_file_api_versions(project_api_version):
                    self.logger.info("\nUpdate Complete!")
                else:
                    self.logger.error("\nUpdate Failed.")
            else:
                self.logger.info("\nUpdate Skipped. Confirmation was not received.")

        elif option.lower() == "2":
            self.logger.info("***Starting Delete Standard Fields Utility***")

            confirmation = input("\nThis will DELETE all Standard/Core Salesforce fields from all object folders within force-app/main/default/objects. Are you sure you want to continue? (y/n) Default y:") or 'y'
            if confirmation.lower() == 'y':
                delete_standard_fields()
                self.logger.info("Update Complete!")
            else:
                self.logger.info("\nUpdate Skipped. Confirmation was not received.")

        elif option.lower() == "3":
            print("RUNNING MASS RENAME TOOL\nWARNING: This tool is still new so please review all changes which is makes.\nWARNING: The following Prefixes are Ignored - sdo_, xdo_, db_\nThe following directories are ignored within force-app/main/default: settings,quickActions,layouts,corswhitelistorigins,roles and standardValueSets")

            warning_input = input("\nAre you happy to proceed? (y/n) : ")

            if warning_input and warning_input.lower() == 'y':
                prefix = input("What prefix do you want to assign to custom files and folders? (e.g. FINS) : ")

                set_interactive_mode = False
                interactive_mode = input("Do you want to be prompted about any potential changes? (y/n) : ")
                if interactive_mode and interactive_mode.lower() == 'y':
                    set_interactive_mode = True

                assign_prefix_to_files(prefix=prefix, interactive_mode=set_interactive_mode)

                print("REMEMBER TO CHECK CHANGES AND TEST DEPLOYMENT")

            else:
                print("Confirmation not received, exiting.")
                exit()
        elif option.lower() == "4":
            file_input = input("\n\nPlease provide the relevant path to the txt file within the project, which holds the names of the objects. (There should be one object api name per line.) : ")
            if file_input and os.path.exists(file_input):
                create_external_id_field(file_input)
                self.logger.info("Update Complete!")
        elif option.lower() == "5":
            target_org_alias = input("Please enter the alias of the connected org: ")
            metadata_diff = compare_metadata(target_org_alias)
            if metadata_diff:
                print("Differences found:")
                print(metadata_diff)
                if input("\nWould you like to push these changes? (y/n) ").lower() == 'y':
                    push_result = push_changes(target_org_alias)
                    print("Push result:")
                    print(push_result)
            else:
                print("No differences found")

            if os.path.exists('src'):
                shutil.rmtree('src')

            if os.path.exists('mdapipkg'):
                shutil.rmtree('mdapipkg')

            if os.path.exists('upgrade_src'):
                shutil.rmtree('upgrade_src')
        elif option.lower() == "6":
            perm_set_name = input("What name would you like to give to the permission set? ")
            if perm_set_name:
                create_permission_set_file(perm_set_name.replace(" ", "_"), perm_set_name)
                self.logger.info("Permission Set Generated!")
        elif option.lower() == "7":
            print("LOADING STACK VIEWER")
            output_method = input("\n Would you like to output to terminal or to a text file? (terminal/file) : ") or "terminal"

            if output_method and (output_method.lower() == "terminal" or output_method.lower() == "file"):
                generate_stack_view(output=output_method.lower())

            else:
                print("Invalid Output Method")
        elif option.lower() == "8":
            migrate()
        elif option.lower() == "e":
            self.logger.info("Exiting Q Brix Mass Operations Utility")
            exit()
        elif option == "t":
            print("test execution")
        else:
            self.logger.info("Invalid Menu Option Entered. Please choose a valid option from the list above.")
            self._run_task()
