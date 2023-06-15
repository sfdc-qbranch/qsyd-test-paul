from time import sleep

from Browser import ElementState, SelectAttribute
from cumulusci.robotframework.base_library import BaseLibrary
from qbrix.robot.QbrixSharedKeywords import QbrixSharedKeywords
from cumulusci.robotframework.SalesforceAPI import SalesforceAPI


class QbrixSalesCloudKeywords(BaseLibrary):

    def __init__(self):
        super().__init__()
        self._browser = None
        self._salesforceapi = None
        self.shared = QbrixSharedKeywords()

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

    def enable_forecasts(self):
        """Go directly to the Field Service admin page"""

        enable_forecasts_toggle = "span.slds-checkbox_off"
        self.shared.go_to_setup_admin_page("Forecasting3Settings/home")
        visible = "visible" in self.browser.get_element_states(enable_forecasts_toggle)
        if visible:
            self.browser.click(enable_forecasts_toggle)
            sleep(2)

    def enable_contacts_to_multiple_accounts(self):
        """
        Enables Contacts to Multiple Accounts Feature in the Salesforce Org
        """

        ctma_selector = "iframe >>> label:has-text('Allow users to relate a contact to multiple accounts')"

        self.shared.go_to_setup_admin_page("AccountSettings/home")
        self.shared.wait_for_page_title("Account Settings")
        self.browser.click("iframe >>> :nth-match(input:has-text('Edit'),1)")
        self.browser.wait_for_elements_state(ctma_selector, ElementState.visible, '10s')
        checked = "checked" in self.browser.get_element_states(ctma_selector)
        if not checked:
            toggle_switch = self.browser.get_element(ctma_selector)
            self.browser.click(toggle_switch)
            self.browser.click("iframe >>> :nth-match(input:has-text('Save'), 2)")
            sleep(10)

    def enable_sales_engagement(self):
        """ Enables Sales Engagement """

        self.shared.go_to_setup_admin_page("SalesEngagement/home", 5)

        button_selector = f"{self.shared.iframe_handler()} button.slds-button:has-text('Set Up and Enable Sales Engagement')"

        if "visible" in self.browser.get_element_states(button_selector):
            self.browser.click(button_selector)
            sleep(20)


    def enable_sales_aggreements(self):
        """ Enables Sales Agreements """

        self.shared.go_to_setup_admin_page("SalesAgreementSettings/home", 5)

        button_selector = f"{self.shared.iframe_handler()} button.slds-button:has-text('Enable Sales Agreements')"

        if "visible" in self.browser.get_element_states(button_selector):
            self.browser.click(button_selector)
            sleep(20)
        

    def set_guest_on_channel_menu(self, channel_menu_api_name):

        """ Sets the Channel Menu Guest API Setting. Expects the Channel Menu API Name (not the label)"""

        self.shared.go_to_setup_admin_page("ChannelMenuDeployments/home")

        self.browser.click(f"tr:has-text('{channel_menu_api_name}') >> a.slds-button")
        sleep(1)
        self.browser.click(".branding-actions > .scrollable > .uiMenuItem:nth-child(2) > a")
        sleep(3)
        visible = "visible" in self.browser.get_element_states("a.supportAPIButton:has-text('Enable on')")
        if visible:
            self.browser.click("a.supportAPIButton:has-text('Enable on')")
            sleep(5)

    def update_forecast_hierarchy_settings(self):
        """ Sets the default SDO configuration for Forecasting """
        self.shared.go_to_setup_admin_page("Forecasting3Role/home", 8)

        # Enable Admin User for the CEO Role
        visible = "visible" in self.browser.get_element_states(
            "iframe >>> :nth-match(a:text-is('Enable Users'):right-of(span.label:text-is('CEO')),1)")
        if visible:
            self.browser.click("iframe >>> :nth-match(a:text-is('Enable Users'):right-of(span.label:text-is('CEO')),1)")
            sleep(5)
            existing_list = self.browser.get_select_options("iframe >>> #duel_select_1")

            results = self.salesforceapi.soql_query(f"SELECT FirstName, LastName FROM User WHERE IsActive=true and ProfileId IN (SELECT ID FROM Profile WHERE Name = 'System Administrator') AND UserRoleId IN (SELECT ID FROM UserRole WHERE Name = 'CEO') AND FirstName != '' AND LastName != 'Bot'")
            if results and results["totalSize"] > 0:
                for record in results["records"]:
                    name = record["FirstName"] + ' ' + record["LastName"]
                    existing_list = self.browser.get_select_options("iframe >>> #duel_select_1")

                    print(f"name: {name}")
                    print(existing_list)


                    changes_made = False
                    if len(existing_list) > 0 and not any(d['label'] == name for d in existing_list):
                        self.browser.select_options_by("iframe >>> td.selectCell:has-text('Available Users') >> select",SelectAttribute.text, name)
                        self.browser.click("iframe >>> img.rightArrowIcon")
                        changes_made = True
                
                if changes_made:
                    self.browser.click("iframe >>> .btn:text-is('Save')")
                else:
                    self.browser.click("iframe >>> .btn:text-is('Cancel')")

            
            sleep(8)

        # Setup Elliot Executive for VP of Sales - User.007
        results = self.salesforceapi.soql_query(f"SELECT id FROM User WHERE External_ID__c ='User.007'")
        if results and results["totalSize"] > 0:
            visible = "visible" in self.browser.get_element_states(
                "iframe >>> :nth-match(img.plus:left-of(span.label:text-is('CEO')),1)")
            if visible:
                self.browser.click("iframe >>> :nth-match(img.plus:left-of(span.label:text-is('CEO')),1)")
                sleep(3)
                self.browser.click("iframe >>> span:has-text('VP of Sales') >> a:text-is('Enable Users')")
                sleep(5)
                existing_list = self.browser.get_select_options("iframe >>> #duel_select_1")
                if len(existing_list) > 0 and not any(d['label'] == 'Elliot Executive' for d in existing_list):
                    self.browser.select_options_by("iframe >>> td.selectCell:has-text('Available Users') >> select",
                                                SelectAttribute.text, "Elliot Executive")
                    self.browser.click("iframe >>> img.rightArrowIcon")
                    sleep(1)
                    self.browser.click("iframe >>> .btn:text-is('Save')")
                else:
                    self.browser.click("iframe >>> .btn:text-is('Cancel')")
                sleep(2)
                

        sleep(10)

    def enable_opportunity_splits(self):
        """
        Enables Opportunity Splits
        """
        self.shared.go_to_setup_admin_page("OpportunitySplitSetup/home")
        self.browser.wait_for_elements_state(f"{self.shared.iframe_handler()} h1.splitSetupHeader:has-text('Opportunity Splits')", ElementState.visible, '30s')
        sleep(5)
        visible = "visible" in self.browser.get_element_states(f"{self.shared.iframe_handler()} input.button:text-is('Set Up Opportunity Splits')")
        if visible:
            button_to_click = self.browser.get_element(f"{self.shared.iframe_handler()} input.button:text-is('Set Up Opportunity Splits')")
            self.browser.click(button_to_click)
            self.browser.wait_for_elements_state(f"{self.shared.iframe_handler()} input.button:text-is('Save')", ElementState.visible, '30s')
            sleep(2)
            save_button_to_click = self.browser.get_element(f"{self.shared.iframe_handler()} input.button:text-is('Save')")
            self.browser.click(save_button_to_click)
            sleep(4)
            self.browser.wait_for_elements_state(f"{self.shared.iframe_handler()} input.btn:text-is('Enable')", ElementState.visible, '30s')
            sleep(2)
            enable_button_to_click = self.browser.get_element(f"{self.shared.iframe_handler()} input.btn:text-is('Enable')")
            self.browser.click(enable_button_to_click)
            self.browser.wait_for_elements_state(f"{self.shared.iframe_handler()} input.btn:text-is('Save')", ElementState.visible, '30s')
            sleep(3)
            enable_button_to_click = self.browser.get_element(f"{self.shared.iframe_handler()} input.btn:text-is('Save')")
            self.browser.click(enable_button_to_click)
            sleep(10)
