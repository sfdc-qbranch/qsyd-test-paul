from time import sleep

from Browser import ElementState, SelectAttribute
from cumulusci.robotframework.base_library import BaseLibrary
from qbrix.robot.QbrixSharedKeywords import QbrixSharedKeywords


class QbrixSurveysKeywords(BaseLibrary):

    def __init__(self):
        super().__init__()
        self._browser = None
        self.shared = QbrixSharedKeywords()

    @property
    def browser(self):
        if self._browser is None:
            self._browser = self.builtin.get_library_instance("Browser")
        return self._browser

    def enable_surveys(self):
        """
        Enables Salesforce Survey Setting in target Salesforce Org
        """
        sleep(5)
        try:
            self.shared.go_to_setup_admin_page("SurveySettings/home", 12)
            survey_toggle = "[class=\"toggle slds-p-left_medium\"]"

            if self.browser.get_element_count(survey_toggle) == 1:
                self.browser.wait_for_elements_state(survey_toggle, ElementState.visible, '30s')
                toggle_switch = self.browser.get_element(survey_toggle)

                # use hover and click for aura toggle to behave
                self.browser.hover(toggle_switch)
                self.browser.click(toggle_switch)
                sleep(10)
        except Exception as e:
            self.browser.take_screenshot()
            raise e

    def set_survey_default_community(self, communityname: str):
        """
        Sets the Default Community for Surveys
        :param communityname: Name of the Community to be used with Salesforce Surveys
        """
        if communityname is None:
            raise Exception("A Community Name must be specified")

        self.enable_surveys()
        sleep(5)

        # Routing Type
        self.browser.select_options_by("[class=\"slds-select\"]", SelectAttribute.text, communityname)
        sleep(2)
