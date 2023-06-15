import json
from time import sleep
import os

from Browser import ElementState, SelectAttribute
from cumulusci.robotframework.base_library import BaseLibrary
from qbrix.robot.QbrixSharedKeywords import QbrixSharedKeywords
from cumulusci.robotframework.SalesforceAPI import SalesforceAPI


class QbrixCMS(BaseLibrary):

    def __init__(self):
        super().__init__()
        self._browser = None
        self.shared = QbrixSharedKeywords()
        self._salesforceapi = None

    @property
    def browser(self):
        if self._browser is None:
            self._browser = self.builtin.get_library_instance("Browser")
        return self._browser

    @property
    def salesforceapi(self):
        if self._salesforceapi is None:
            self._salesforceapi = SalesforceAPI()
        return self._salesforceapi

    def go_to_digital_experiences(self):
        self.shared.go_to_app("Digital Experiences")

    def download_all_content(self):

        # Get Workspace Names
        results = self.salesforceapi.soql_query(f"SELECT Name FROM ManagedContentSpace WHERE IsDeleted=False")
        if results["totalSize"] == 0:
            return

        # Download content from each workspace
        for workspace in results["records"]:
            self.download_cms_content(workspace["Name"])

    def upload_cms_import_file(self, file_path, workspace):

        """
        Uploads the Content from the CMS import .zip file
        @return:
        @param file_path: Relative path to the .zip file containing the export
        @param workspace: Name of the workspace to upload the content to
        """

        self.go_to_digital_experiences()
        sleep(5)

        # Go To Workspace Page
        if workspace:

            # Get the Application ID
            results = self.salesforceapi.soql_query(
                f"SELECT Id FROM ManagedContentSpace where Name = '{workspace}' LIMIT 1")

            if results["totalSize"] == 1:
                app_id = results["records"][0]["Id"]

                # Go to the app
                self.browser.go_to(f"{self.cumulusci.org.instance_url}/lightning/cms/spaces/{app_id}", timeout='30s')

                # Open Import Menu
                iframe_handler = self.shared.iframe_handler()
                drop_down_menu_selector = f"{iframe_handler} div.slds-page-header__row >> button.slds-button:has-text('Show menu')"
                import_button_selector = f"{iframe_handler} div.slds-page-header__row >> lightning-menu-item.slds-dropdown__item:has-text('Import Content')"

                self.browser.click(drop_down_menu_selector)
                sleep(1)
                upload_promise = self.browser.promise_to_upload_file(file_path)
                self.browser.click(import_button_selector)
                sleep(2)
                self.browser.click("div.modal-body >> span.slds-checkbox >> span.slds-checkbox_faux")
                sleep(1)
                self.browser.click("button.slds-button:has-text('Import')")
                sleep(5)
                self.browser.click("button.slds-button:text('ok')")
                sleep(2)

        else:
            print("Workspace cannot be None. Skipping")
            return

    def download_cms_content(self, workspace):

        """
        Initiate the export of a workspace to a content .zip file (which is emailed to the admin)
        @param workspace: Name of workspace
        @return:
        """

        self.go_to_digital_experiences()
        sleep(5)

        # Go To Workspace Page
        if workspace:

            # Get the Application ID
            results = self.salesforceapi.soql_query(f"SELECT Id FROM ManagedContentSpace where Name = '{workspace}' LIMIT 1")

            if results["totalSize"] == 1:
                app_id = results["records"][0]["Id"]

                # Go to the app
                self.browser.go_to(f"{self.cumulusci.org.instance_url}/lightning/cms/spaces/{app_id}", timeout='30s')
                iframe_handler = self.shared.iframe_handler()

                # Enhanced workspace handler
                if self.browser.get_element_count(f"{iframe_handler} lightning-badge.slds-badge:has-text('Enhanced'):visible") > 0:
                    return

                # Select all checkboxes
                no_items = False 
                while True:

                    total_cms_elements = self.browser.get_element(f"{iframe_handler} p.slds-page-header__meta-text")

                    if total_cms_elements:

                        innertext_for_total = self.browser.get_property(f"{iframe_handler} p.slds-page-header__meta-text", "innerText")

                        if innertext_for_total == "0 item(s)":
                            no_items = True
                            break

                        if innertext_for_total and "+" not in str(innertext_for_total):
                            break

                        if innertext_for_total and "+" in str(innertext_for_total):
                            elements = self.browser.get_elements(f"{iframe_handler} table.slds-table >> sfdc_cms-content-check-box-button")
                            for elem in elements:
                                self.browser.scroll_to_element(elem)

                    else:
                        break
                
                if no_items:
                    return

                elements = self.browser.get_elements(f"{iframe_handler} table.slds-table >> sfdc_cms-content-check-box-button")
                for elem in elements:
                    self.browser.scroll_to_element(elem)
                    self.browser.click(elem)

                # Open Export Menu

                drop_down_menu_selector = f"{iframe_handler} div.slds-page-header__row >> button.slds-button:has-text('Show menu')"
                import_button_selector = f"{iframe_handler} div.slds-page-header__row >> lightning-menu-item.slds-dropdown__item:has-text('Export Content')"

                self.browser.click(drop_down_menu_selector)
                sleep(1)

                self.browser.click(import_button_selector)
                sleep(2)
                self.browser.click(f"{iframe_handler} button.slds-button:has-text('Export')")
                sleep(5)

    def create_workspace(self, workspace_name, channels=[], enhanced_workspace=True):

        """
        Create a new workspace
        @param workspace_name: Name of the workspace. This must be unique from other workspaces
        @param channels: Optional channels you want to target. Defaults to all available channels
        @param enhanced_workspace: Set to True if you are creating an Enhanced workspace, otherwise set to False. Defaults to True.
        @return:
        """

        # Check for existing workspace
        results = self.salesforceapi.soql_query(f"SELECT Id FROM ManagedContentSpace where Name = '{workspace_name}' LIMIT 1")

        if results["totalSize"] == 1:
            print("Workspace exists already, skipping.")
            return

        # Go to Digital Experience Home and initiate Workspace creation
        self.go_to_digital_experiences()
        sleep(3)
        self.browser.go_to(f"{self.cumulusci.org.instance_url}/lightning/cms/home/", timeout='30s')
        sleep(3)
        self.browser.click(f"{self.shared.iframe_handler()} span.label:text-is('Create a CMS Workspace'):visible")

        # Enter initial information
        sleep(2)
        self.browser.click("lightning-input:has-text('Name') >> input.slds-input")
        self.browser.fill_text("lightning-input:has-text('Name') >> input.slds-input", workspace_name)

        # Handle enhanced workspace option
        if enhanced_workspace:
            self.browser.click("span.slds-text-heading_medium:text-is('Enhanced CMS Workspace')")

        # Handle Channel Selection
        self.browser.click("button.nextButton:visible")
        sleep(2)
        if len(channels) > 0:
            for channel in channels:
                if self.browser.get_element_count(f"tr.slds-hint-parent:has-text('{channel}')"):
                    self.browser.click(f"tr.slds-hint-parent:has-text('{channel}') >> div.slds-checkbox_add-button")
        else:
            for checkbox_add_button in self.browser.get_elements("div.slds-checkbox_add-button"):
                self.browser.click(checkbox_add_button)

        # Handle Contributors
        self.browser.click("button.nextButton:visible")
        sleep(2)
        for checkbox_add_button in self.browser.get_elements("div.forceSelectableListViewSelectionColumn"):
            self.browser.click(checkbox_add_button)

        # Handle Contributor Access Levels
        self.browser.click("button.nextButton:visible")
        sleep(2)
        for combo_box in self.browser.get_elements("lightning-picklist:visible"):
            self.browser.click(combo_box)
            sleep(1)
            self.browser.click("span.slds-listbox__option-text:has-text('Content Admin'):visible")

        # Handle Language
        self.browser.click("button.nextButton:visible")
        sleep(2)

        if not enhanced_workspace:
            self.browser.click("button.slds-button:has-text('Move selection to Selected'):visible")
            self.browser.click("lightning-combobox.slds-form-element:has-text('Default Language'):visible")
            self.browser.click("lightning-base-combobox-item:has-text('English (United States)'):visible")

        # Complete Screen
        self.browser.click("button.nextButton:visible")
        sleep(1)
        self.browser.click("button.nextButton:visible")

    def generate_product_media_file(self):

        """
        Generates a Product Media Mapping File, which stores information about Product List Images, Product Detail Images and Attachments related to the products.
        @return: .json file is created within the project and stored at this path: cms_data/product_images.json
        """

        # Get All Active Products which have attached ElectronicMedia
        results = self.salesforceapi.soql_query(f"SELECT Id, External_ID__c, Name from Product2 WHERE Id IN (Select ProductId from ProductMedia)")

        if results["totalSize"] == 0:
            print("No Products found with attached media")
            return

        result_dict = {}
        self.shared.go_to_app("Commerce - Admin")

        for product in results["records"]:

            product_dict = {}

            # Set External ID
            product_dict.update({"External_ID__c": product["External_ID__c"]})

            self.browser.go_to(f"{self.cumulusci.org.instance_url}/lightning/r/Product2/{product['Id']}/view", timeout='30s')
            sleep(4)

            self.browser.click(f"div.uiTabBar >> span.title:text-is('Media')")
            sleep(10)

            # Get Product Detail Images (Max. 8)
            if self.browser.get_element_count(f"article.slds-card:has-text('Product Detail Images'):visible >> img.fileCardImage:visible") > 0:
                product_detail_image_list = []
                product_detail_images = self.browser.get_elements(f"article.slds-card:has-text('Product Detail Images'):visible >> img.fileCardImage:visible")
                if product_detail_images:
                    for prod in product_detail_images:
                        prod_property = self.browser.get_property(prod, "alt")
                        if prod_property:
                            print(prod_property)
                            product_detail_image_list.append(prod_property)

                if len(product_detail_image_list) > 0:
                    product_dict.update({"ProductDetailImages": product_detail_image_list})

            # Get Product List Image (Max. 1)
            if self.browser.get_element_count(f"article.slds-card:has-text('Product List Image'):visible >> img.fileCardImage:visible") > 0:
                product_image_list = []
                product_images = self.browser.get_elements(f"article.slds-card:has-text('Product List Image'):visible >> img.fileCardImage:visible")
                if product_images:
                    for prod in product_images:
                        prod_property = self.browser.get_property(prod, "alt")
                        if prod_property:
                            print(prod_property)
                            product_image_list.append(prod_property)

                if len(product_image_list) > 0:
                    product_dict.update({"ProductImages": product_image_list})

            # Get Attachments (Max. 5)
            if self.browser.get_element_count(f"article.slds-card:has-text('Attachments'):visible >> span.slds-file__text") > 0:
                attachment_list = []
                attachment_images = self.browser.get_elements(f"article.slds-card:has-text('Attachments'):visible >> span.slds-file__text")
                if attachment_images:
                    for prod in attachment_images:
                        prod_property = self.browser.get_property(prod, "title")
                        if prod_property:
                            print(prod_property)
                            attachment_list.append(prod_property)

                if len(attachment_list) > 0:
                    product_dict.update({"Attachments": attachment_list})

            self.browser.click(f"li.oneConsoleTabItem:has-text('{product['Name']}'):visible >> div.close")

            result_dict.update({f"Product_{product['External_ID__c']}": product_dict})

        # Save dict to file
        if not os.path.exists("cms_data"):
            os.makedirs("cms_data", exist_ok=True)

        with open("cms_data/product_images.json", "w") as save_file:
            json.dump(result_dict, save_file, indent=2)

    def reassign_product_media_files(self):

        """
        Assigns Media Files stored in Salesforce CMS to the relevant Products in the target org.
        """

        # Check for default file
        if not os.path.exists("cms_data/product_images.json"):
            print("Missing CMS Definition File. Location: cms_data/product_images.json")
            raise Exception("Required file for robot is missing: cms_data/product_images.json. Please check the file and try again.")

        # Process Mapping File
        with open("cms_data/product_images.json", "r") as cms_file:
            product_dict = json.load(cms_file)

        if product_dict:

            # Go to Admin Console
            self.shared.go_to_app("Commerce - Admin")

            # Setup Selectors
            media_tab_selector = "div.uiTabBar >> span.title:text-is('Media')"

            # Process Product Records
            for product in dict(product_dict).items():

                results = self.salesforceapi.soql_query(f"SELECT Id, External_ID__c, Name from Product2 WHERE External_ID__c = '{product[1]['External_ID__c']}' LIMIT 1")

                if results["totalSize"] == 0:
                    print(f"No Products found for the External ID Provided {product[1]['External_ID__c']}. Skipping...")
                    continue

                try:
                    # Go To Record Page for Product and select Media tab
                    self.browser.go_to(f"{self.cumulusci.org.instance_url}/lightning/r/Product2/{results['records'][0]['Id']}/view", timeout='30s')
                    self.browser.wait_for_elements_state(media_tab_selector, ElementState.visible, timeout="10s")
                    self.browser.click(media_tab_selector)
                    sleep(8)
                except TimeoutError:
                    print(f"Unable to access the Media tab for the current Product record with Id ({results['records'][0]['Id']}). Skipping...")
                    continue
                except Exception as e:
                    raise e

                # Process Product Detail Images
                if "ProductDetailImages" in dict(product[1]).keys() and self.browser.get_element_count(f"article.slds-card:has-text('Product Detail Images'):visible >> img.fileCardImage:visible") < 8:

                    for product_detail_image in list(product[1]["ProductDetailImages"]):

                        # Check Max. Number of Product Detail Images has not been reached
                        if self.browser.get_element_count(f"article.slds-card:has-text('Product Detail Images'):visible >> img.fileCardImage:visible") == 8:
                            print("The maximum number of images have already been assigned to the Product. Skipping...")
                            continue

                        # Check that CMS content has not already been assigned
                        skip = False
                        if self.browser.get_element_count(f"article.slds-card:has-text('Product Detail Images'):visible >> img.fileCardImage:visible") > 0:
                            product_detail_images = self.browser.get_elements(f"article.slds-card:has-text('Product Detail Images'):visible >> img.fileCardImage:visible")
                            if product_detail_images:
                                for prod in product_detail_images:
                                    prod_property = self.browser.get_property(prod, "alt")
                                    print(f"Found alt text: {prod_property}")
                                    if prod_property:
                                        if prod_property in list(product[1]["ProductDetailImages"]):
                                            print("Skipping duplicate...")
                                            skip = True
                        if skip:
                            continue

                        # Assign New Image

                        self.browser.click("article.slds-card:has-text('Product Detail Images'):visible >> :nth-match(button.slds-button:text-is('Add Image'), 1)")
                        self.browser.wait_for_elements_state("sfdc_cms-content-uploader-header.slds-col:visible >> input.slds-input", ElementState.visible, timeout="10s")
                        self.browser.fill_text("sfdc_cms-content-uploader-header.slds-col:visible >> input.slds-input", product_detail_image)

                        # Handle Search Results
                        try:
                            sleep(2)
                            search_results = self.browser.get_elements(f"tr.slds-hint-parent:has-text('{product_detail_image}'):visible")
                            if len(search_results) == 0:
                                self.browser.click(f"button.slds-button:text-is('Cancel')")
                                continue
                            if len(search_results) > 0:
                                self.browser.click("tr:has(span:text-matches('^{}$')) >> th >> span.slds-checkbox_faux".format(product_detail_image))
                                self.browser.click(f"button.slds-button:text-is('Save')")
                                self.browser.wait_for_elements_state(media_tab_selector, ElementState.visible, timeout="15s")
                                self.browser.click(media_tab_selector)
                        except TimeoutError:
                            print("Unable to find any matches for search results. Skipping...")
                            self.browser.click(f"button.slds-button:text-is('Cancel')")
                            continue
                else:
                    print("The maximum number of images have already been assigned to the Product or there are no Product Detail Images to process. Skipping...")

                # Process Product List Image

                if "ProductImages" in dict(product[1]).keys() and self.browser.get_element_count(f"article.slds-card:has-text('Product List Image'):visible >> img.fileCardImage:visible") < 1:

                    for product_image in list(product[1]["ProductImages"]):

                        # Check Max. Number of Product List Images has not been reached
                        if self.browser.get_element_count(f"article.slds-card:has-text('Product List Image'):visible >> img.fileCardImage:visible") == 1:
                            print("The maximum number of images have already been assigned to the Product. Skipping...")
                            continue

                        # Check that CMS content has not already been assigned
                        skip = False
                        if self.browser.get_element_count(f"article.slds-card:has-text('Product List Image'):visible >> img.fileCardImage:visible") > 0:
                            product_images = self.browser.get_elements(f"article.slds-card:has-text('Product List Image'):visible >> img.fileCardImage:visible")
                            if product_images:
                                for prod in product_images:
                                    prod_property = self.browser.get_property(prod, "alt")
                                    print(f"Found alt text: {prod_property}")
                                    if prod_property:
                                        if prod_property in list(product[1]["ProductImages"]):
                                            print("Skipping duplicate...")
                                            skip = True
                        if skip:
                            continue

                        # Assign New Image

                        self.browser.click("article.slds-card:has-text('Product List Image'):visible >> :nth-match(button.slds-button:text-is('Add Image'), 1)")
                        self.browser.wait_for_elements_state("sfdc_cms-content-uploader-header.slds-col:visible >> input.slds-input", ElementState.visible, timeout="10s")
                        self.browser.fill_text("sfdc_cms-content-uploader-header.slds-col:visible >> input.slds-input", product_image)

                        # Handle Search Results
                        try:
                            sleep(2)
                            search_results = self.browser.get_elements(f"tr.slds-hint-parent:has-text('{product_image}'):visible")
                            if len(search_results) == 0:
                                self.browser.click(f"button.slds-button:text-is('Cancel')")
                                continue
                            if len(search_results) > 0:
                                self.browser.click("tr:has(span:text-matches('^{}$')) >> td >> span.slds-radio".format(product_image))
                                self.browser.click(f"button.slds-button:text-is('Save')")
                                self.browser.wait_for_elements_state(media_tab_selector, ElementState.visible, timeout="15s")
                                self.browser.click(media_tab_selector)
                        except TimeoutError:
                            print("Unable to find any matches for search results. Skipping...")
                            self.browser.click(f"button.slds-button:text-is('Cancel')")
                            continue
                else:
                    print("The maximum number of images have already been assigned to the Product or there are no Product List Images to process. Skipping...")

                # Process Attachments

                if "Attachments" in dict(product[1]).keys() and self.browser.get_element_count(f"article.slds-card:has-text('Attachments'):visible >> span.slds-file__text") < 5:

                    for product_attachment in list(product[1]["Attachments"]):

                        # Check Max. Number of Attachments has not been reached
                        if self.browser.get_element_count(f"article.slds-card:has-text('Attachments'):visible >> span.slds-file__text") == 5:
                            print("The maximum number of attachments have already been assigned to the Product. Skipping...")
                            continue

                        # Check that CMS content has not already been assigned
                        skip = False
                        if self.browser.get_element_count(f"article.slds-card:has-text('Attachments'):visible >> span.slds-file__text") > 0:
                            product_attachments = self.browser.get_elements(f"article.slds-card:has-text('Attachments'):visible >> span.slds-file__text")
                            if product_attachments:
                                for prod in product_attachments:
                                    prod_property = self.browser.get_property(prod, "title")
                                    print(f"Found title text: {prod_property}")
                                    if prod_property:
                                        if prod_property in list(product[1]["Attachments"]):
                                            print("Skipping duplicate...")
                                            skip = True
                        if skip:
                            continue

                        # Assign New Attachment

                        self.browser.click("article.slds-card:has-text('Attachments'):visible >> :nth-match(button.slds-button:text-is('Add Attachment'), 1)")
                        self.browser.wait_for_elements_state("sfdc_cms-content-uploader-header.slds-col:visible >> input.slds-input", ElementState.visible, timeout="10s")
                        self.browser.fill_text("sfdc_cms-content-uploader-header.slds-col:visible >> input.slds-input", product_attachment)

                        # Handle Search Results
                        try:
                            sleep(2)
                            search_results = self.browser.get_elements(f"tr.slds-hint-parent:has-text('{product_attachment}'):visible")
                            if len(search_results) == 0:
                                self.browser.click(f"button.slds-button:text-is('Cancel')")
                                continue
                            if len(search_results) > 0:
                                self.browser.click("tr:has(span:text-matches('^{}$')) >> th >> span.slds-checkbox_faux".format(product_attachment))
                                self.browser.click(f"button.slds-button:text-is('Save')")
                                self.browser.wait_for_elements_state(media_tab_selector, ElementState.visible, timeout="15s")
                                self.browser.click(media_tab_selector)
                        except TimeoutError:
                            print("Unable to find any matches for search results. Skipping...")
                            self.browser.click(f"button.slds-button:text-is('Cancel')")
                            continue
                else:
                    print("The maximum number of attachments have already been assigned to the Product or there are no Product Attachments to process. Skipping...")

                # Close Tab
                try:
                    self.browser.click(f"li.oneConsoleTabItem:has-text('{results['records'][0]['Name']}'):visible >> div.close")
                except:
                    continue
