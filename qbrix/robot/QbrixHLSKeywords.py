from time import sleep
from Browser import ElementState, SelectAttribute
from cumulusci.robotframework.base_library import BaseLibrary
from qbrix.robot.QbrixSharedKeywords import QbrixSharedKeywords
from cumulusci.robotframework.SalesforceAPI import SalesforceAPI


class QbrixHLSKeywords(BaseLibrary):

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

    def enable_care_plans(self):
        """
        Enables Care Plans for HLS
        """
        self.shared.go_to_setup_admin_page("CarePlanSettings/home")
        self.browser.wait_for_elements_state("p:text-is('Care Plans')", ElementState.visible, '30s')
        checked = "checked" in self.browser.get_element_states(
            ":nth-match(label:has-text('Disabled'), 1)")
        if not checked:
            toggle_switch = self.browser.get_element(
                ":nth-match(label:has-text('Disabled'), 1)")
            self.browser.click(toggle_switch)
            sleep(1)

    def enable_assessments(self):
        """
        Enables Assessments for HLS
        """
        self.shared.go_to_setup_admin_page("AssessmentSettings/home")
        self.browser.wait_for_elements_state("h3:text-is('Guest User Assessments')", ElementState.visible, '30s')
        checked = "checked" in self.browser.get_element_states(".toggle:has-text('Disabled')")
        if not checked:
            self.browser.click(".toggle:has-text('Disabled')")
            sleep(5)
            self.browser.wait_for_elements_state("button:has-text('Turn On')", ElementState.visible, '30s')
            self.browser.click("button:has-text('Turn On')")
            sleep(5)

    def enable_care_plans_grantmaking(self):
        """
        Enables Care Plans Grantmaking for HLS
        """
        self.shared.go_to_setup_admin_page("CarePlanSettings/home")
        self.browser.wait_for_elements_state("p:text-is('Care Plans')", ElementState.visible, '30s')
        checked = "checked" in self.browser.get_element_states(
            ":nth-match(label:has-text('Disabled'), 1)")
        if not checked:
            toggle_switch = self.browser.get_element(
                ":nth-match(label:has-text('Disabled'), 1)")
            self.browser.click(toggle_switch)
            sleep(1)

        checked2 = "checked" in self.browser.get_element_states(
            ":nth-match(label:has-text('Disabled'), 2)")
        if not checked2:
            toggle_switch = self.browser.get_element(
                ":nth-match(label:has-text('Disabled'), 2)")
            self.browser.click(toggle_switch)
            sleep(2)
            if "visible" in self.browser.get_element_states("button:has-text('Enable')"):
                QbrixSharedKeywords().click_button_with_text("Enable")
                sleep(5)
