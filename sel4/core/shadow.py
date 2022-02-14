"""

"""
import time

from pydantic import Field, validate_arguments
from selenium.common.exceptions import JavascriptException, WebDriverException
from selenium.webdriver.remote.webelement import WebElement

from sel4.utils.typeutils import OptionalInt

from ..utils.retries import retry_call
from . import constants, page_actions


def _fail_if_invalid_shadow_selector_usage(selector: str = Field(default="", strict=True, min_length=1)):
    ...


@validate_arguments
def is_shadow_selector(selector: str = Field(default="", strict=True, min_length=1)):
    """
    Determine if the current selector is a shadow selector

    :param selector: aa strict string with minimum length of 1
    :return: True if is a shadow selector, False otherwise
    """
    _fail_if_invalid_shadow_selector_usage(selector)
    if "::shadow " in selector:
        return True
    return False


@validate_arguments()
def shadow_click(
    selector: str = Field(default="", strict=True, min_length=1),
    timeout: OptionalInt = None,
):
    element = get_shadow_element(selector, timeout=timeout, must_be_visible=True)
    element.click()


@validate_arguments
def get_shadow_element(
    selector: str = Field(default="", strict=True, min_length=1),
    timeout: OptionalInt = None,
    must_be_visible=False,
):
    self.wait_for_ready_state_complete()
    if timeout is None:
        timeout = constants.SMALL_TIMEOUT
    elif timeout == 0:
        timeout = 0.1  # Use for: is_shadow_element_* (* = present/visible)
    if self.timeout_multiplier and timeout == constants.SMALL_TIMEOUT:
        timeout = self.__get_new_timeout(timeout)
    _fail_if_invalid_shadow_selector_usage(selector)
    if "::shadow " not in selector:
        raise TypeError('A Shadow DOM selector must contain at least one "::shadow "!')
    selectors = selector.split("::shadow ")
    element = self.get_element(selectors[0])
    selector_chain = selectors[0]
    is_present = False
    for selector_part in selectors[1:]:
        shadow_root = None
        if self.is_chromium() and int(self.__get_major_browser_version()) >= 96:
            try:
                shadow_root = element.shadow_root
            except Exception:
                if self.browser == "chrome":
                    chrome_dict = self.driver.capabilities["chrome"]
                    chrome_dr_version = chrome_dict["chromedriverVersion"]
                    chromedriver_version = chrome_dr_version.split(" ")[0]
                    major_c_dr_version = chromedriver_version.split(".")[0]
                    if int(major_c_dr_version) < 96:
                        upgrade_to = "latest"
                        major_browser_version = self.__get_major_browser_version()
                        if int(major_browser_version) >= 96:
                            upgrade_to = str(major_browser_version)
                        message = (
                            "You need to upgrade to a newer\n"
                            "version of chromedriver to interact\n"
                            "with Shadow root elements!\n"
                            "(Current driver version is: %s)"
                            "\n(Minimum driver version is: 96.*)"
                            "\nTo upgrade, run this:"
                            '\n"seleniumbase install chromedriver %s"' % (chromedriver_version, upgrade_to)
                        )
                        raise Exception(message)
                if timeout != 0.1:  # Skip wait for special 0.1 (See above)
                    time.sleep(2)
                try:
                    shadow_root = element.shadow_root
                except Exception:
                    raise Exception("Element {%s} has no shadow root!" % selector_chain)
        else:  # This part won't work on Chrome 96 or newer.
            # If using Chrome 96 or newer (and on an old Python version),
            #     you'll need to upgrade in order to access Shadow roots.
            # Firefox users will likely hit:
            #     https://github.com/mozilla/geckodriver/issues/1711
            #     When Firefox adds support, switch to element.shadow_root

            def retry_execute_script(e: WebElement) -> WebElement:
                return self.execute_script("return arguments[0].shadowRoot", e)

            try:
                shadow_root = retry_call(
                    retry_execute_script,
                    element,
                    exceptions=JavascriptException,
                    tries=2,
                    delay=0.5,
                    backoff=2,
                )
                shadow_root = self.execute_script("return arguments[0].shadowRoot", element)
            except JavascriptException:
                time.sleep(2)
                shadow_root = self.execute_script("return arguments[0].shadowRoot", element)
        if timeout == 0.1 and not shadow_root:
            raise Exception("Element {%s} has no shadow root!" % selector_chain)
        elif not shadow_root:
            time.sleep(2)  # Wait two seconds for the shadow root to appear
            shadow_root = self.execute_script("return arguments[0].shadowRoot", element)
            if not shadow_root:
                raise Exception("Element {%s} has no shadow root!" % selector_chain)
        selector_chain += "::shadow "
        selector_chain += selector_part
        try:
            if self.is_chromium() and int(self.__get_major_browser_version()) >= 96:
                if timeout == 0.1:
                    element = shadow_root.find_element(By.CSS_SELECTOR, value=selector_part)
                else:
                    found = False
                    for i in range(int(timeout) * 4):
                        try:
                            element = shadow_root.find_element(By.CSS_SELECTOR, value=selector_part)
                            is_present = True
                            if must_be_visible:
                                if not element.is_displayed():
                                    raise Exception("Shadow Root element not visible!")
                            found = True
                            break
                        except Exception:
                            time.sleep(0.2)
                            continue
                    if not found:
                        element = shadow_root.find_element(By.CSS_SELECTOR, value=selector_part)
                        is_present = True
                        if must_be_visible and not element.is_displayed():
                            raise Exception("Shadow Root element not visible!")
        except Exception:
            error = "not present"
            the_exception = "NoSuchElementException"
            if must_be_visible and is_present:
                error = "not visible"
                the_exception = "ElementNotVisibleException"
            msg = "Shadow DOM Element {%s} was %s after %s seconds!" % (
                selector_chain,
                error,
                timeout,
            )
            page_actions.timeout_exception(the_exception, msg)
    return element
