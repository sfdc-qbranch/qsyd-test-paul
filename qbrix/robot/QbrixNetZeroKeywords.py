from time import sleep
from cumulusci.robotframework.base_library import BaseLibrary
from qbrix.robot.QbrixSharedKeywords import QbrixSharedKeywords


class QbrixNetZeroKeywords(BaseLibrary):

    def __init__(self):
        super().__init__()
        self._browser = None
        self.shared = QbrixSharedKeywords()

    @property
    def browser(self):
        if self._browser is None:
            self._browser = self.builtin.get_library_instance("Browser")
        return self._browser

    def enable_net_zero(self):
        """
        Enables NetZero Cloud Setting
        """
        self.shared.go_to_setup_admin_page("NetZeroPrefs/home", 5)
        # Check and Click Main Net Zero Button/Toggle
        selector_main_toggle = "div.slds-grid:has-text('Allow users to turn on Net Zero Cloud in this org.') >> span.slds-checkbox_faux"
        main_toggle_checked = "checked" in self.browser.get_element_states(selector_main_toggle)
        if not main_toggle_checked:
            self.browser.click(selector_main_toggle)
            main_toggle_checked = True
        if main_toggle_checked:
            # Check and Enable Carbon Emissions
            selector_carbon_emissions_toggle = "div.slds-grid:has-text('Calculate carbon emissions related to the energy use data.') >> span.slds-checkbox_faux"
            carbon_emissions_checked = "checked" in self.browser.get_element_states(selector_carbon_emissions_toggle)
            if not carbon_emissions_checked:
                self.browser.click(selector_carbon_emissions_toggle)
                carbon_emissions_checked = True
            if carbon_emissions_checked:
                # Check and Enable Building Data
                selector_building_data = "div.slds-grid:has-text('Search for and calculate building energy intensities and use them to fill data gaps.') >> span.slds-checkbox_faux"
                building_data_checked = "checked" in self.browser.get_element_states(selector_building_data)
                if not building_data_checked:
                    self.browser.click(selector_building_data)
