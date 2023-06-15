from time import sleep
from Browser import ElementState, SelectAttribute
from cumulusci.robotframework.base_library import BaseLibrary
from qbrix.robot.QbrixSharedKeywords import QbrixSharedKeywords
from cumulusci.robotframework.SalesforceAPI import SalesforceAPI


class QbrixFINSKeywords(BaseLibrary):

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

    def enable_interest_tagging(self):
        """
        Enables Interest Tagging for FINS Cloud
        """
        enable_toggle = "span.slds-checkbox_off"
        self.shared.go_to_setup_admin_page("InterestTaggingSettings/home")
        self.browser.wait_for_elements_state("p:text-is('Let users access interest tags feature')", ElementState.visible, '30s')
        checked = "checked" in self.browser.get_element_states(
            ":nth-match(label:has-text('Off'), 1)")
        if not checked:
            toggle_switch = self.browser.get_element(
                ":nth-match(label:has-text('off'), 1)")
            self.browser.click(toggle_switch)
            sleep(1)

    def enable_record_alert_access(self):
        """
        Enables Record Alert Access for Financial Services
        """
        enable_toggle = "span.slds-checkbox_off"
        self.shared.go_to_setup_admin_page("RecordAlertOrgSettings/home")
        self.browser.wait_for_elements_state("p:text-is('Record Alert Preferences')", ElementState.visible, '30s')
        checked = "checked" in self.browser.get_element_states(
            ":nth-match(label:has-text('Off'), 1)")
        if not checked:
            toggle_switch = self.browser.get_element(
                ":nth-match(label:has-text('off'), 1)")
            self.browser.click(toggle_switch)
            sleep(1)
        checked2 = "checked" in self.browser.get_element_states(
            ":nth-match(label:has-text('Off'), 2)")
        if not checked2:
            toggle_switch2 = self.browser.get_element(
                ":nth-match(label:has-text('off'), 2)")
            self.browser.click(toggle_switch2)
            sleep(1)

    def enable_business_rules_engine(self):
        """
        Enables Business Rules Engine for Financial Services
        """
        self.shared.go_to_setup_admin_page("BREDecisionTableAccess/home")
        self.browser.wait_for_elements_state("span:text-is('Business Rules Engine Settings')", ElementState.visible, '30s')
        checked = "checked" in self.browser.get_element_states(".toggle:has-text('Disabled')")
        if not checked:
            self.browser.click(".toggle:has-text('Disabled')")
            sleep(5)
            self.browser.wait_for_elements_state("button:has-text('Enable')", ElementState.visible, '30s')
            self.browser.click("button:has-text('Enable')")
            sleep(5)

    def enable_financial_account_setting(self):
        """
        Enables Business Rules Engine for Financial Services
        """
        enable_toggle = "span.slds-checkbox_off"
        self.shared.go_to_setup_admin_page("FscServiceExcellenceSettings/home")
        self.browser.wait_for_elements_state("p:text-is('Datasource Preferences')", ElementState.visible, '30s')
        checked = "checked" in self.browser.get_element_states(
            ":nth-match(label:has-text('Off'), 1)")
        if not checked:
            toggle_switch = self.browser.get_element(
                ":nth-match(label:has-text('Off'), 1)")
            self.browser.click(toggle_switch)
            sleep(1)

    def enable_actionable_segmentation_settings(self):
        """
        Enables Business Rules Engine for Financial Services
        """
        self.shared.go_to_setup_admin_page("ActionableSegmentationSettings/home")
        self.browser.wait_for_elements_state("span:text-is('Actionable Segmentation Settings')", ElementState.visible, '30s')
        checked = "checked" in self.browser.get_element_states("label:has-text('Disabled')")
        if not checked:
            self.browser.click("label:has-text('Disabled')")
            sleep(5)
            self.browser.click("button:has-text('Enable')")
            sleep(5)