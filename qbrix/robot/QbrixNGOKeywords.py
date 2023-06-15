from time import sleep
from Browser import ElementState, SelectAttribute
from cumulusci.robotframework.base_library import BaseLibrary
from qbrix.robot.QbrixSharedKeywords import QbrixSharedKeywords
from cumulusci.robotframework.SalesforceAPI import SalesforceAPI


class QbrixNGOKeywords(BaseLibrary):

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

    def enable_program_benefits(self):
        """
        Enables Program and Benefit Management Settings for NGO Cloud
        """
        self.shared.go_to_setup_admin_page("BenefitManagementSettings/home")
        self.browser.wait_for_elements_state("p:text-is('Program and Benefit Management')", ElementState.visible, '30s')
        checked = "checked" in self.browser.get_element_states(
            ":nth-match(label:has-text('Disabled'), 1)")
        checked2 = "checked" in self.browser.get_element_states(
            ":nth-match(label:has-text('Disabled'), 2)")
        if not checked:
            toggle_switch = self.browser.get_element(
                ":nth-match(label:has-text('Disabled'), 1)")
            self.browser.click(toggle_switch)
            sleep(1)
        if not checked2:
            toggle_switch2 = self.browser.get_element(
                ":nth-match(label:has-text('Disabled'), 2)")
            self.browser.click(toggle_switch2)
