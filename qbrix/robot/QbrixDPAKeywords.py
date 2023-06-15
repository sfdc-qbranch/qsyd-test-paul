from time import sleep
from Browser import ElementState, SelectAttribute
from cumulusci.robotframework.base_library import BaseLibrary
from qbrix.robot.QbrixSharedKeywords import QbrixSharedKeywords
from cumulusci.robotframework.SalesforceAPI import SalesforceAPI


class QbrixDPAKeywords(BaseLibrary):

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

    def activate_omnistudio_metadata(self):
        self.go_to_lightning_setup_omnistudio_settings()
        self.enable_omnistudio_metadata()
        
    def activate_standard_omnistudio_runtime(self):
        self.go_to_lightning_setup_omnistudio_settings()
        self.enable_standard_omnistudio_runtime()
        
    def deactivate_standard_omnistudio_runtime(self):
        self.go_to_lightning_setup_omnistudio_settings()
        self.disable_standard_omnistudio_runtime()
        
    def activate_dataraptor_versioning(self):
        self.go_to_lightning_setup_omnistudio_settings()
        self.enable_dataraptor_versioning()
        
    def deactivate_dataraptor_versioning(self):
        self.go_to_lightning_setup_omnistudio_settings()
        self.disable_dataraptor_versioning()
    
    def go_to_lightning_setup_omnistudio_settings(self):
        """
        Goes directly to set up OmniStudio Settings Settings in Lightning UI
        """
        self.browser.go_to(f"{self.cumulusci.org.instance_url}/lightning/setup/OmniStudioSettings/home")
        self.browser.wait_for_elements_state("h1:has-text('OmniStudio Settings')", ElementState.visible, '30s')
        
        
    def enable_omnistudio_metadata(self):
        """
        Enable once. Toggle will be disabled after that.
        """
        sleep(10)
        # 1 = OmniStudio Metadata - index 0
        # 2 = Standard OmniStudio Runtime - index 1
        # 3 = DataRaptor Versioning - index 2
        
        js_var = self.build_toggle_on_js(0)
        self.browser.evaluate_javascript(":nth-match(runtime_omnistudio-pref-toggle,1)",js_var)
        sleep(15)
        try:
            self.shared.click_button_with_text("OK")
            sleep(10)
        except:
            print('fail silently')
            
        self.go_to_lightning_setup_omnistudio_settings()
        
        
    def enable_standard_omnistudio_runtime(self):
        sleep(10)
        # 1 = OmniStudio Metadata - index 0
        # 2 = Standard OmniStudio Runtime - index 1
        # 3 = DataRaptor Versioning - index 2
        
        js_var = self.build_toggle_on_js(1)
        self.browser.evaluate_javascript(":nth-match(runtime_omnistudio-pref-toggle,2)",js_var)
        sleep(15)
        self.go_to_lightning_setup_omnistudio_settings()
        
        
    def disable_standard_omnistudio_runtime(self):
        sleep(10)
        # 1 = OmniStudio Metadata - index 0
        # 2 = Standard OmniStudio Runtime - index 1
        # 3 = DataRaptor Versioning - index 2
        
        js_var = self.build_toggle_off_js(1)
        self.shared.log_to_file(js_var)
        self.browser.evaluate_javascript(":nth-match(runtime_omnistudio-pref-toggle,2)",js_var)
        sleep(15)
        self.go_to_lightning_setup_omnistudio_settings()
        
        
    def enable_dataraptor_versioning(self):
        sleep(10)
        # 1 = OmniStudio Metadata - index 0
        # 2 = Standard OmniStudio Runtime - index 1
        # 3 = DataRaptor Versioning - index 2
        
        js_var = self.build_toggle_on_js(2)
        self.browser.evaluate_javascript(":nth-match(runtime_omnistudio-pref-toggle,3)",js_var)
        sleep(15)
        
        self.go_to_lightning_setup_omnistudio_settings()
        
        
    def disable_dataraptor_versioning(self):
        sleep(10)
        # 1 = OmniStudio Metadata - index 0
        # 2 = Standard OmniStudio Runtime - index 1
        # 3 = DataRaptor Versioning - index 2
        
        js_var = self.build_toggle_off_js(2)
        self.browser.evaluate_javascript(":nth-match(runtime_omnistudio-pref-toggle,3)",js_var)
        sleep(15)
        self.go_to_lightning_setup_omnistudio_settings()
        
        
    def build_toggle_on_js(self,toggleindex:int):
        #use replace over format to get around { field error on multiple line string
        return """(elements)=>
                {
                    isDisabled=document.querySelectorAll('runtime_omnistudio-pref-toggle')[{toggleindex}].shadowRoot.querySelector('lightning-input').shadowRoot.querySelector('input').getAttribute('disabled');
                    if(isDisabled==null)
                    {
                        isChecked =document.querySelectorAll('runtime_omnistudio-pref-toggle')[{toggleindex}].shadowRoot.querySelector('lightning-input').getAttribute('checked');
                        if(isChecked==null)
                        {
                            document.querySelectorAll('runtime_omnistudio-pref-toggle')[{toggleindex}].shadowRoot.querySelector('lightning-input').shadowRoot.querySelector('input').click();
                        }
                    }
                }""".replace("{toggleindex}",str(toggleindex))
                
    def build_toggle_off_js(self,toggleindex:int):
        #use replace over format to get around { field error on multiple line string
        return """(elements)=>
                {
                    isDisabled=document.querySelectorAll('runtime_omnistudio-pref-toggle')[{toggleindex}].shadowRoot.querySelector('lightning-input').shadowRoot.querySelector('input').getAttribute('disabled');
                    if(isDisabled==null)
                    {
                        isChecked =document.querySelectorAll('runtime_omnistudio-pref-toggle')[{toggleindex}].shadowRoot.querySelector('lightning-input').getAttribute('checked');
                        if(isChecked!=null)
                        {
                            document.querySelectorAll('runtime_omnistudio-pref-toggle')[{toggleindex}].shadowRoot.querySelector('lightning-input').shadowRoot.querySelector('input').click();
                        }
                    }
                }""".replace("{toggleindex}",str(toggleindex))
                
        
                
        