from time import sleep
from Browser import ElementState, SelectAttribute
from cumulusci.robotframework.base_library import BaseLibrary
from qbrix.robot.QbrixSharedKeywords import QbrixSharedKeywords
from cumulusci.robotframework.SalesforceAPI import SalesforceAPI


class QbrixManufacturingKeywords(BaseLibrary):

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

    def get_store_id(self, store_name):
        if store_name is None:
            raise Exception("Profile Name must be specified")

        results = self.salesforceapi.soql_query(f"SELECT Id from WebStore where Name = '{store_name}' LIMIT 1")

        if results["totalSize"] == 1:
            return results["records"][0]["Id"]

        return None

    def start_reindex(self, store_name):

        index_button_selector = ":nth-match(button.slds-button:text-is('Rebuild Index'):visible, 1)"
        index_confirmation_selector = ":nth-match(button.slds-button:text-is('Rebuild'):visible, 1)"

        # Go To Index Page
        store_id = self.get_store_id(store_name)
        if store_id:
            self.browser.go_to(
                f"{self.cumulusci.org.instance_url}/lightning/page/commerceSearch?lightning__webStoreId={store_id}&ws=%2Flightning%2Fr%2FWebStore%2F{store_id}%2Fview")
            self.browser.wait_for_elements_state(index_button_selector, ElementState.visible, '10s')
            if "enabled" in self.browser.get_element_states(index_button_selector):
                self.browser.click(index_button_selector)
                sleep(2)
                self.browser.click(index_confirmation_selector)
                sleep(2)

    def enable_sales_agreements(self):
        """
        Enables Sales Agreement Setting in Salesforce Setup
        """
        self.shared.go_to_setup_admin_page("SalesAgreementSettings/home")
        #self.browser.wait_for_elements_state("h1:text-is('Sales Agreements')", ElementState.visible, '30s')
        sleep(5)
        if not "checked" in self.browser.get_element_states("div.slds-grid:has-text('Enable Sales Agreements') >> label.slds-checkbox_toggle"):
            self.browser.click("div.slds-grid:has-text('Enable Sales Agreements') >> label.slds-checkbox_toggle")
            sleep(1)

    def enable_manufacturing_service_console(self):
        """
        Enables Service Console for Manufacturing Setting in Salesforce Setup
        """
        enable_mfgservice_toggle = "span.slds-checkbox_off"
        self.shared.go_to_setup_admin_page("MfgServiceExcellenceSettings/home")
        self.browser.wait_for_elements_state("h2:text-is('Service Console for Manufacturing')", ElementState.visible, '30s')
        visible = "visible" in self.browser.get_element_states(enable_mfgservice_toggle)
        if visible:
            self.browser.click(enable_mfgservice_toggle)
            sleep(2)

    def enable_account_manager_targets(self):
        """
        Enables Account Manager Targets for Manufacturing Setting in Salesforce Setup
        """
        enable_toggle = "span.slds-checkbox_off"
        self.shared.go_to_setup_admin_page("AcctMgrTargetSettings/home")
        sleep(10)
        visible = "visible" in self.browser.get_element_states(enable_toggle)
        if visible:
            self.browser.click(enable_toggle)
            sleep(2)

    def enable_partner_visit_management(self):
        """
        Enables Partner Visit Management for Manufacturing Setting in Salesforce Setup
        """
        enable_toggle = "span.slds-checkbox_off"
        self.shared.go_to_setup_admin_page("MfgPartnerVisitMgmtSettings/home")
        self.browser.wait_for_elements_state("h2:text-is('Partner Visit Management')", ElementState.visible, '30s')
        visible = "visible" in self.browser.get_element_states(enable_toggle)
        if visible:
            self.browser.click(enable_toggle)
            sleep(2)

    def enable_partner_performance_management(self):
        """
        Enables Partner Performance Management for Manufacturing Setting in Salesforce Setup
        """
        enable_toggle = "span.slds-checkbox_off"
        self.shared.go_to_setup_admin_page("MfgPartnerPerfMgmtSettings/home")
        self.browser.wait_for_elements_state("h2:text-is('Partner Performance Management')", ElementState.visible, '30s')
        visible = "visible" in self.browser.get_element_states(enable_toggle)
        if visible:
            self.browser.click(enable_toggle)
            sleep(2)

    def enable_group_membership(self):
        """
        Enables Group Membership Settings Salesforce Setup
        """
        enable_toggle = "span.slds-checkbox_off"
        self.shared.go_to_setup_admin_page("GroupMembershipSettings/home")
        self.browser.wait_for_elements_state("p:text-is('Group Membership')", ElementState.visible, '30s')
        visible = "visible" in self.browser.get_element_states(enable_toggle)
        if visible:
            self.browser.click(enable_toggle)
            sleep(2)

    def enable_partner_lead_management(self):
        """
        Enables Partner Lead Management Settings Salesforce Setup
        """
        enable_toggle = "span.slds-checkbox_off"
        self.shared.go_to_setup_admin_page("MfgPartnerLeadMgmtSettings/home")
        self.browser.wait_for_elements_state("h2:text-is('Partner Lead Management')", ElementState.visible, '30s')
        visible = "visible" in self.browser.get_element_states(enable_toggle)
        if visible:
            self.browser.click(enable_toggle)
            sleep(2)
            

    def enable_program_based_business(self):
        """
        Enables Program Based Business for Manufacturing Setting in Salesforce Setup
        """
        enable_toggle = "span.slds-checkbox_off"
        self.shared.go_to_setup_admin_page("MfgProgramTemplates/home")
        self.browser.wait_for_elements_state("h2:text-is('Warranty Administration')", ElementState.visible, '30s')
        visible = "visible" in self.browser.get_element_states(enable_toggle)
        if visible:
            self.browser.click(enable_toggle)
            sleep(2)

    def enable_warranty_lifecycle_management(self):
        """
        Enables  Warranty Lifecycle Management for Manufacturing Setting in Salesforce Setup
        """
        enable_toggle = "span.slds-checkbox_off"
        self.shared.go_to_setup_admin_page("MfgServiceSettings/home")
        self.browser.wait_for_elements_state("h2:text-is('Warranty Administration')", ElementState.visible, '30s')
        visible = "visible" in self.browser.get_element_states(enable_toggle)
        if visible:
            self.browser.click(enable_toggle)
            sleep(2)


    def enable_automotive_cloud_setting(self):
        """
        Enables Automotive Cloud Setting
        """
        enable_autoCloud = "span.slds-checkbox_off"
        self.shared.go_to_setup_admin_page("AutomotiveFoundationSettings/home")
        self.browser.wait_for_elements_state("h2:text-is('Automotive')", ElementState.visible, '30s')
        visible = "visible" in self.browser.get_element_states(enable_autoCloud)
        if visible:
            self.browser.click(enable_autoCloud)
            sleep(2)

    def enable_automotive_cloud_service_console_setting(self):
        """
        Enables Automotive Cloud Service Console Setting
        """
        enable_autoServi = "span.slds-checkbox_off"
        self.shared.go_to_setup_admin_page("AutomotiveServiceExcellenceSettings/home")
        self.browser.wait_for_elements_state("h2:text-is('Service Console for Automotive')", ElementState.visible, '30s')
        visible = "visible" in self.browser.get_element_states(enable_autoServi)
        if visible:
            self.browser.click(enable_autoServi)
            sleep(2)