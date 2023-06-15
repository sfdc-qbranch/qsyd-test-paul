from time import sleep
from robot.libraries.BuiltIn import BuiltIn
from Browser import SupportedBrowsers

class QRobot:

  def __init__(self):
        self._builtin = None
        self._cumulusci = None
        self._salesforce_api = None
        self._browser = None

  @property
  def salesforce_api(self):
      if getattr(self, "_salesforce_api", None) is None:
          self._salesforce_api = self.builtin.get_library_instance(
              "cumulusci.robotframework.SalesforceAPI"
          )
      return self._salesforce_api

  @property
  def builtin(self):
      if getattr(self, "_builtin", None) is None:
          self._builtin = BuiltIn()
      return self._builtin

  @property
  def cumulusci(self):
      if getattr(self, "_cumulusci", None) is None:
          self._cumulusci = self.builtin.get_library_instance(
              "cumulusci.robotframework.CumulusCI"
          )
      return self._cumulusci

  @property
  def browser(self):
      if self._browser is None:
          self._browser = self.builtin.get_library_instance("Browser")
      return self._browser

  def open_q_browser(self, record_video=False):

    # Set Defaults for Browser Instance
    browser = self.builtin.get_variable_value("${BROWSER}", "chrome")
    headless = browser.startswith("headless")
    browser_type = browser[8:] if headless else browser
    browser_type = "chromium" if browser_type == "chrome" else browser_type
    browser_enum = getattr(SupportedBrowsers, browser_type, None)
    login_url = self.cumulusci.login_url()

    # Enable Video Recording (if requested)
    rec=None
    if record_video:
      rec={"dir": "../video"}

    # Open New Browser
    browser_id = self.browser.new_browser(browser=browser_enum, headless=headless)
    context_id = self.browser.new_context(
        viewport={"width": 1920, "height": 1080}, recordVideo=rec
    )
    self.browser.set_browser_timeout("240 seconds")
    sleep(1)

    # Login to Org
    page_details = self.browser.new_page()
    #page = self.browser.get_current_page()
    #page.set_default_navigation_timeout(120000)

    retries = 0
    while retries < 4:
        try:
            self.browser.go_to(login_url, timeout="120s")
            sleep(1)
            if "lightning" in str(self.browser.get_url()):
                break
        except Exception as e:
            print(e)
            self.browser.take_screenshot()
            retries += 1

    if retries >= 3:
        raise Exception("Unable to launch robot. Please try again.")

    # Browse to Setup Page if not there already
    if not str(self.browser.get_url()).endswith("/lightning/setup/SetupOneHome/home"):
      self.browser.go_to(f"{self.cumulusci.org.instance_url}/lightning/setup/SetupOneHome/home", timeout="120s")

    return browser_id, context_id, page_details

  def close_q_browser(self):
    self.browser.close_browser("ALL")
