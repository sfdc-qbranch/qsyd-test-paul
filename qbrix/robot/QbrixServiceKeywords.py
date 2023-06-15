from time import sleep

from Browser import ElementState, SelectAttribute
from cumulusci.robotframework.base_library import BaseLibrary
from qbrix.robot.QbrixSharedKeywords import QbrixSharedKeywords
from robot.api import logger


class QbrixServiceKeywords(BaseLibrary):

    def __init__(self):
        super().__init__()
        self._browser = None
        self.shared = QbrixSharedKeywords()

    @property
    def browser(self):
        if self._browser is None:
            self._browser = self.builtin.get_library_instance("Browser")
        return self._browser

    def enable_incident_management(self):
        """" Enables Incident Management """
        self.shared.go_to_setup_admin_page("IncidentManagement/home")
        sleep(8)
        checked = "checked" in self.browser.get_element_states(
            ":nth-match(label:has-text('Customer Service Incident Management'), 2)")
        if not checked:
            toggle_switch = self.browser.get_element(
                ":nth-match(label:has-text('Customer Service Incident Management'), 2)")
            self.browser.click(toggle_switch)
            sleep(1)

    def enable_slack_integration(self):
        """ Enables Slack Integration with the target org """
        self.shared.go_to_setup_admin_page("SlackSetupAssistant/home")
        sleep(2)
        checked = "checked" in self.browser.get_element_states("label:has-text('Unaccepted')")
        if not checked:
            self.browser.click("label:has-text('Unaccepted')")
            sleep(3)
        self.browser.wait_for_elements_state("label:has-text('Accepted')", ElementState.visible, '15s')

    def enable_case_swarming(self):
        self.enable_slack_integration()
        self.shared.go_to_setup_admin_page("SlackServiceApp/home")
        checked = "checked" in self.browser.get_element_states("span.slds-checkbox_faux")
        if not checked:
            self.browser.click("span.slds-checkbox_faux")
            sleep(1)
        sleep(3)
        self.shared.go_to_setup_admin_page("CaseSwarming/home")
        self.browser.wait_for_elements_state("h1:has-text('Swarming')", ElementState.visible, '30s')
        checked = "checked" in self.browser.get_element_states("span.slds-checkbox_faux")
        if not checked:
            self.browser.click("span.slds-checkbox_faux")
            sleep(1)

    def create_chat_button(self):
        self.shared.go_to_setup_admin_page("LiveChatButtonSettings/home")
        sleep(4)
        self.browser.get_element_states(".button:has-text('New')")
        sleep(5)

    def add_case_wrap_up_model(self):
        self.shared.go_to_setup_admin_page("EinsteinCaseClassification/home")
        sleep(2)
        if "visible" in self.browser.get_element_states("button.slds-button:text-is('Get Started')"):
            self.browser.click("button.slds-button:text-is('Get Started')")
        else:
            if "visible" in self.browser.get_element_states("button.slds-button:text-is('New Model')"):
                self.browser.click("button.slds-button:text-is('New Model')")
        self.browser.click("div.slds-visual-picker >> label:has-text('Case Wrap-Up')")
        self.browser.fill_text("label:has-text('Model Name')", "Case Wrap-Up")
        self.browser.click("label:has-text('Model Name')")
        sleep(1)
        self.browser.click("div.modal-footer >> button.slds-button:text-is('Next')")
        sleep(2)
        self.browser.click("div.modal-footer >> button.slds-button:text-is('Next')")
        sleep(2)
        self.browser.click("div.modal-footer >> button.slds-button:text-is('Next')")
        sleep(3)
        self.browser.click("tr:has-text('Case Reason') >> div.slds-checkbox_add-button")
        self.browser.click("tr:has-text('Case Type') >> div.slds-checkbox_add-button")
        self.browser.click("tr:has-text('Escalated') >> div.slds-checkbox_add-button")
        self.browser.click("tr:has-text('Priority') >> div.slds-checkbox_add-button")
        sleep(3)
        self.browser.click("div.modal-footer >> button.slds-button:text-is('Next')")
        self.browser.click("div.modal-footer >> button.slds-button:text-is('Finish')")
        sleep(10)

    def create_case_classification_model(self):
        self.shared.go_to_setup_admin_page("EinsteinCaseClassification/home")
        sleep(2)
        if "visible" in self.browser.get_element_states("button.slds-button:text-is('Get Started')"):
            self.browser.click("button.slds-button:text-is('Get Started')")
        else:
            if "visible" in self.browser.get_element_states("button.slds-button:text-is('New Model')"):
                self.browser.click("button.slds-button:text-is('New Model')")
        self.browser.fill_text("label:has-text('Model Name')", "SDO - Classification")
        sleep(1)
        self.browser.click("div.modal-footer >> button.slds-button:text-is('Next')")
        sleep(2)
        self.browser.click("div.modal-footer >> button.slds-button:text-is('Next')")
        sleep(2)
        self.browser.click("div.modal-footer >> button.slds-button:text-is('Next')")
        sleep(3)
        self.browser.click("tr:has-text('Case Reason') >> div.slds-checkbox_add-button")
        sleep(3)
        self.browser.click("div.modal-footer >> button.slds-button:text-is('Next')")
        self.browser.click("div.modal-footer >> button.slds-button:text-is('Finish')")
        sleep(10)


    def messaging_components_setup(self):
        """
        Runs the Messaging Components Setup
        """
        iframe_handler = self.shared.iframe_handler()

        # define the attributes of 3 message components
        list_of_msgs = [
            {
                "name": "ConversationAcknowledgement",
                "developer_name": "SDO_Messaging_ConversationAcknowledgement",
                "msg": "Hello, thanks for reaching out. We will be with you shortly.",
                "description": "Opening conversation acknowledgment"
            },
            {
                "name": "StartConversation",
                "developer_name": "SDO_Messaging_StartConversation",
                "msg": "You are now connected to an agent, thank you for waiting.",
                "description": "Start conversation text, and picks up when someone accepts the work."
            },
            {
                "name": "EndConversation",
                "developer_name": "SDO_Messaging_EndConversation",
                "msg": "Thanks for contacting us today. Have a great day.",
                "description": "This displays when the conversation has ended"
            }
        ]


        for one_msg in list_of_msgs:
            # Make sure we are on Messaging Components page
            self.shared.go_to_setup_admin_page("ConversationMessageDefinitions/home")
            self.browser.wait_for_elements_state("h1:has-text('Messaging Components')", ElementState.visible, '30s')
            sleep(2)


            self.shared.click_button_with_text("New Component")
            self.shared.click_button_with_text("Next")
            sleep(1)
            self.browser.click("div.slds-visual-picker__figure:has-text('Auto-Response')")
            sleep(1)
            self.shared.click_button_with_text("Next")
            self.browser.fill_text(f"{iframe_handler} textarea[name='Title']",one_msg["msg"])
            sleep(1)
            self.shared.click_button_with_text("Next")
            self.browser.fill_text(f"{iframe_handler} input[name='label']",one_msg["name"])
            self.browser.fill_text(f"{iframe_handler} input[name='fullName']",one_msg["developer_name"])
            self.browser.fill_text(f"{iframe_handler} textarea[name='description']",one_msg["description"])
            self.shared.click_button_with_text("Done")

            sleep(4)

        return

