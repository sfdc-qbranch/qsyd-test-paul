from time import sleep

from Browser import ElementState, SelectAttribute
from cumulusci.robotframework.base_library import BaseLibrary
from qbrix.robot.QbrixSharedKeywords import QbrixSharedKeywords


class QbrixToolingKeywords(BaseLibrary):

    def __init__(self):
        super().__init__()
        self._browser = None
        self.shared = QbrixSharedKeywords()

    @property
    def browser(self):
        if self._browser is None:
            self._browser = self.builtin.get_library_instance("Browser")
        return self._browser

    # -----------------------------------------------------------------------------------------------------------------------------------------
    # Q BRANCH TOOLING FUNCTIONS
    # -----------------------------------------------------------------------------------------------------------------------------------------

    def enable_admin_auth_for_connected_app(self, connected_app_label):
        try:
            self.shared.go_to_setup_admin_page("ConnectedApplication/home")
            iframe_selector = self.shared.iframe_handler()
            self.browser.wait_for_elements_state(f"{iframe_selector} h1:text-is('Connected Apps')", ElementState.visible, "15s")
            self.browser.click(f"{iframe_selector} a:text-is('{connected_app_label}')")
            self.browser.wait_for_elements_state(f"{iframe_selector} h2.mainTitle:text-is('Connected App Detail')", ElementState.visible, "15s")

            if self.browser.get_element_count(f"{iframe_selector} td.dataCol:text-is('Admin approved users are pre-authorized')") == 0:
                self.browser.click(f"{iframe_selector} .btn:has-text('Edit Policies')")
                self.browser.wait_for_elements_state(f"{iframe_selector} h2.mainTitle:text-is('Connected App Edit')", ElementState.visible, "15s")
                self.browser.select_options_by(f"{iframe_selector} #userpolicy", SelectAttribute.text, "Admin approved users are pre-authorized")
                sleep(10)
                self.browser.click(f"{iframe_selector} .btn:has-text('Save')")
                self.browser.wait_for_elements_state(f"{iframe_selector} h2.mainTitle:text-is('Connected App Detail')", ElementState.visible, "15s")
        except Exception as e:
            self.browser.take_screenshot()
            raise e

    def enable_q_passport(self):
        """ Enables Q Passport Connected App Settings"""
        self.enable_admin_auth_for_connected_app("Q_Passport")

    def enable_demo_boost(self):
        """ Enables Demo Boost Connected App Settings"""
        self.enable_admin_auth_for_connected_app("Demo Boost")

    def enable_demo_wizard(self):
        """ Enables Demo Wizard Connected App Settings"""
        self.enable_admin_auth_for_connected_app("Demo Wizard")

    def enable_data_tool(self):
        """ Enables Data Tool Connected App Settings"""
        self.enable_admin_auth_for_connected_app("NXDO Data Tool")
        iframe_selector = self.shared.iframe_handler()
        self.browser.wait_for_elements_state(f"{iframe_selector} .btn:has-text('Manage Profiles')", ElementState.visible, "15s")
        self.browser.click(f"{iframe_selector} .btn:has-text('Manage Profiles')")
        self.browser.wait_for_elements_state(f"{iframe_selector} h1:text-is('Application Profile Assignment')", ElementState.visible, "15s")
        if not "checked" in self.browser.get_element_states(f"{iframe_selector} tr:has-text('System Administrator') >> input"):
            self.browser.click(f"{iframe_selector} tr:has-text('System Administrator') >> input")
            self.browser.click(f"{iframe_selector} .btn:has-text('Save')")
            sleep(2)
