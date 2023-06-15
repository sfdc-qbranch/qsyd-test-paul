from time import sleep

from Browser import ElementState, SelectAttribute
from cumulusci.robotframework.base_library import BaseLibrary
from qbrix.robot.QbrixSharedKeywords import QbrixSharedKeywords


class QbrixSchedulerKeywords(BaseLibrary):

    def __init__(self):
        super().__init__()
        self._browser = None
        self.shared = QbrixSharedKeywords()

    @property
    def browser(self):
        if self._browser is None:
            self._browser = self.builtin.get_library_instance("Browser")
        return self._browser

    def enable_scheduler(self):
        """ Enables Salesforce Scheduler """
        
        settings_page_url = "LightningSchedulerSettings/home"
        wait_for_title = "h2:has-text('Event Management')"
        
        # Go To Scheduler Setup
        self.shared.go_to_setup_admin_page(settings_page_url)
        self.browser.wait_for_elements_state(wait_for_title, ElementState.visible, '30s')

        # Enable Appointment Distribution
        appointment_dist_selector = "span.slds-form-element__label:has-text('Appointment Distribution')"
        self.browser.wait_for_elements_state(appointment_dist_selector, ElementState.visible, '30s')
        if not "checked" in self.browser.get_element_states(appointment_dist_selector):
            self.browser.click(appointment_dist_selector)
            sleep(2)
            self.shared.go_to_setup_admin_page(settings_page_url)

        # Enable Aggregate Resource Use
        agg_resource_selector = "span.slds-form-element__label:has-text('Aggregate Resource Use')"
        self.browser.wait_for_elements_state(agg_resource_selector, ElementState.visible, '30s')
        if not "checked" in self.browser.get_element_states(agg_resource_selector):
            self.browser.click(agg_resource_selector)
            sleep(2)
            self.shared.go_to_setup_admin_page(settings_page_url)

        # Enable Multi-Resource Scheduling
        multi_resource_selector = "span.slds-form-element__label:has-text('Multi-Resource Scheduling')"
        self.browser.wait_for_elements_state(multi_resource_selector, ElementState.visible, '30s')
        if not "checked" in self.browser.get_element_states(multi_resource_selector):
            self.browser.click(multi_resource_selector)
            sleep(2)

    def create_appointment_assignment_policies(self):
        """ Creates the Appointment Assignment Policies """
        self.shared.go_to_setup_admin_page("AppointmentAssignmentPolicy/home")
        sleep(2)
        self.browser.wait_for_elements_state("iframe >>> .btn:has-text('New')", ElementState.visible, '30s')
        visible = "visible" in self.browser.get_element_states(
            "iframe >>> .listRelatedObject:has-text('Activity based distribution')")
        if not visible:
            self.browser.click("iframe >>> .btn:has-text('New')")
            self.browser.wait_for_elements_state("iframe >>> input[name='MasterLabel']", ElementState.visible, '30s')
            self.browser.fill_text("iframe >>> input[name='MasterLabel']", "Activity based distribution")
            self.browser.fill_text("iframe >>> input[name='DeveloperName']", "Activity_based_distribution")
            self.browser.select_options_by("iframe >>> select[name='PolicyType']", SelectAttribute.text,
                                           "Load Balancing")
            self.browser.select_options_by("iframe >>> select[name='PolicyApplicableDuration']", SelectAttribute.text,
                                           "Parameter-Based")
            self.browser.select_options_by("iframe >>> select[name='UtilizationFactor']", SelectAttribute.text,
                                           "Number of Appointments")
            sleep(2)
            self.browser.click("iframe >>> :nth-match(.btn:has-text('Save'),1)")
            sleep(1)
