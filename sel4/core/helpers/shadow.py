"""

"""
import time
from typing import TYPE_CHECKING

from pydantic import Field, validate_arguments
from selenium.common.exceptions import (
    JavascriptException,
    ElementNotVisibleException,
    WebDriverException
)
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement


from ...utils.typeutils import OptionalInt
from .. import constants
from ...conf import settings


if TYPE_CHECKING:
    from sel4.core.webdriver_test import WebDriverTest


class ShadowElement:
    def __init__(self, proxy: WebDriverTest):
        self._proxy = proxy
        self.driver = proxy.driver

    @validate_arguments
    def _get_shadow_element(
            self,
            selector: str = Field(default="", strict=True, min_length=1),
            timeout: OptionalInt = None,
            must_be_visible=False,
    ):
        self._proxy.wait_for_ready_state_complete()
        if timeout is None:
            timeout = constants.SMALL_TIMEOUT
        elif timeout == 0:
            timeout = 0.1  # Use for: is_shadow_element_* (* = present/visible)
        self._proxy.get_timeout(timeout, constants.SMALL_TIMEOUT)
        if "::shadow " not in selector:
            raise TypeError('A Shadow DOM selector must contain at least one "::shadow "!')
        selectors = selector.split("::shadow ")
        element = self._proxy.get_element(selectors[0])
        selector_chain = selectors[0]
        is_present = False
        for selector_part in selectors[1:]:
            shadow_root = None
            if self._proxy.is_chromium and int(self._proxy.major_browser_version) >= 96:
                try:
                    shadow_root = element.shadow_root
                except WebDriverException:
                    if self.driver.capabilities.get("browserName") == "chrome":
                        chrome_dict = self.driver.capabilities["chrome"]
                        chrome_dr_version = chrome_dict["chromedriverVersion"]
                        chromedriver_version = chrome_dr_version.split(" ")[0]
                        major_c_dr_version = chromedriver_version.split(".")[0]
                        if int(major_c_dr_version) < 96:
                            upgrade_to = "latest"
                            if int(self._proxy.major_browser_version) >= 96:
                                upgrade_to = str(self._proxy.major_browser_version)
                            message = (
                                    "You need to upgrade to a newer\n"
                                    "version of chromedriver to interact\n"
                                    "with Shadow root elements!\n"
                                    "(Current driver version is: %s)"
                                    "\n(Minimum driver version is: 96.*)"
                                    "\nTo upgrade, run this:"
                                    '\n"seleniumbase install chromedriver %s"' % (chromedriver_version, upgrade_to)
                            )
                            raise WebDriverException(message)
                    if timeout != 0.1:
                        time.sleep(2)
                    try:
                        shadow_root = element.shadow_root
                    except Exception:
                        raise Exception("Element {%s} has no shadow root!" % selector_chain)
            if timeout == 0.1 and not shadow_root:
                raise Exception("Element {%s} has no shadow root!" % selector_chain)
            elif not shadow_root:
                time.sleep(2)  # Wait two seconds for the shadow root to appear
                shadow_root = self._proxy.execute_script("return arguments[0].shadowRoot", element)
                if not shadow_root:
                    raise WebDriverException(f"Element {selector_chain} has no shadow root!")
            selector_chain += "::shadow "
            selector_chain += selector_part
            try:
                if self._proxy.is_chromium and int(self._proxy.major_browser_version) >= 96:
                    if timeout == 0.1:
                        element = self.find_element(By.CSS_SELECTOR, value=selector_part)
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
                            except WebDriverException:
                                time.sleep(0.2)
                                continue
                        if not found:
                            element = shadow_root.find_element(By.CSS_SELECTOR, value=selector_part)
                            is_present = True
                            if must_be_visible and not element.is_displayed():
                                raise ElementNotVisibleException("Shadow Root element not visible!")
            except WebDriverException:
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

    @validate_arguments()
    def shadow_click(
            self,
            selector: str = Field(default="", strict=True, min_length=1),
            timeout: OptionalInt = None,
    ):
        element = self._get_shadow_element(selector, timeout=timeout, must_be_visible=True)
        element.click()

    @validate_arguments
    def wait_for_shadow_element_visible(
            self,
            selector: str = Field(default="", strict=True, min_length=1),
            timeout: OptionalInt = None,
    ) -> WebElement:
        return self._get_shadow_element(selector, timeout=timeout, must_be_visible=True)

    @validate_arguments
    def wait_for_shadow_element_present(
            self,
            selector: str = Field(default="", strict=True, min_length=1),
            timeout: OptionalInt = None
    ) -> WebElement:
        return self._get_shadow_element(selector, timeout=timeout)

    def is_shadow_element_enabled(
            self,
            selector: str = Field(default="", strict=True, min_length=1)
    ) -> bool:
        try:
            element = self._get_shadow_element(selector, timeout=0.1)
            return element.is_enabled()
        except WebDriverException:
            return False

    @validate_arguments
    def get_shadow_attribute(
            self,
            attribute_name: str,
            selector: str = Field(default="", strict=True, min_length=1),
            timeout: int = constants.SMALL_TIMEOUT
    ):
        element = self._get_shadow_element(selector, timeout=timeout)
        return element.get_attribute(attribute_name)

    @validate_arguments
    def wait_for_shadow_text_visible(
            self,
            text: str | None,
            selector: str = Field(default="", strict=True, min_length=1)
    ):
        start_ms = time.time() * 1000.0
        stop_ms = start_ms + (constants.SMALL_TIMEOUT * 1000.0)
        for x in range(int(constants.SMALL_TIMEOUT * 10)):
            try:
                actual_text = self.get_shadow_text(selector, timeout=1).strip()
                text = text.strip()
                if text not in actual_text:
                    msg = (
                        "Expected text {%s} in element {%s} was not visible!"
                        % (text, selector)
                    )
                    page_actions.timeout_exception(
                        "ElementNotVisibleException", msg
                    )
                return True
            except Exception:
                now_ms = time.time() * 1000.0
                if now_ms >= stop_ms:
                    break
                time.sleep(0.1)
        actual_text = self.__get_shadow_text(selector, timeout=1).strip()
        text = text.strip()
        if text not in actual_text:
            msg = "Expected text {%s} in element {%s} was not visible!" % (
                text,
                selector,
            )
            page_actions.timeout_exception("ElementNotVisibleException", msg)
        return True


    def wait_for_exact_shadow_text_visible(self, text, selector, timeout):
        start_ms = time.time() * 1000.0
        stop_ms = start_ms + (settings.SMALL_TIMEOUT * 1000.0)
        for x in range(int(settings.SMALL_TIMEOUT * 10)):
            try:
                actual_text = self.__get_shadow_text(
                    selector, timeout=1
                ).strip()
                text = text.strip()
                if text != actual_text:
                    msg = (
                        "Expected exact text {%s} in element {%s} not visible!"
                        "" % (text, selector)
                    )
                    page_actions.timeout_exception(
                        "ElementNotVisibleException", msg
                    )
                return True
            except Exception:
                now_ms = time.time() * 1000.0
                if now_ms >= stop_ms:
                    break
                time.sleep(0.1)
        actual_text = self.__get_shadow_text(selector, timeout=1).strip()
        text = text.strip()
        if text != actual_text:
            msg = (
                "Expected exact text {%s} in element {%s} was not visible!"
                % (text, selector)
            )
            page_actions.timeout_exception("ElementNotVisibleException", msg)
        return True


    def get_shadow_element(
        self, selector, timeout=None, must_be_visible=False
    ):
        self.wait_for_ready_state_complete()
        if timeout is None:
            timeout = settings.SMALL_TIMEOUT
        elif timeout == 0:
            timeout = 0.1  # Use for: is_shadow_element_* (* = present/visible)
        if self.timeout_multiplier and timeout == settings.SMALL_TIMEOUT:
            timeout = self.__get_new_timeout(timeout)
        self.__fail_if_invalid_shadow_selector_usage(selector)
        if "::shadow " not in selector:
            raise Exception(
                'A Shadow DOM selector must contain at least one "::shadow "!'
            )
        selectors = selector.split("::shadow ")
        element = self.get_element(selectors[0])
        selector_chain = selectors[0]
        is_present = False
        for selector_part in selectors[1:]:
            shadow_root = None
            if (
                selenium4
                and self.is_chromium()
                and int(self.__get_major_browser_version()) >= 96
            ):
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
                            major_browser_version = (
                                self.__get_major_browser_version()
                            )
                            if int(major_browser_version) >= 96:
                                upgrade_to = str(major_browser_version)
                            message = (
                                "You need to upgrade to a newer\n"
                                "version of chromedriver to interact\n"
                                "with Shadow root elements!\n"
                                "(Current driver version is: %s)"
                                "\n(Minimum driver version is: 96.*)"
                                "\nTo upgrade, run this:"
                                '\n"seleniumbase install chromedriver %s"'
                                % (chromedriver_version, upgrade_to)
                            )
                            raise Exception(message)
                    if timeout != 0.1:  # Skip wait for special 0.1 (See above)
                        time.sleep(2)
                    try:
                        shadow_root = element.shadow_root
                    except Exception:
                        raise Exception(
                            "Element {%s} has no shadow root!" % selector_chain
                        )
            else:  # This part won't work on Chrome 96 or newer.
                # If using Chrome 96 or newer (and on an old Python version),
                #     you'll need to upgrade in order to access Shadow roots.
                # Firefox users will likely hit:
                #     https://github.com/mozilla/geckodriver/issues/1711
                #     When Firefox adds support, switch to element.shadow_root
                try:
                    shadow_root = self.execute_script(
                        "return arguments[0].shadowRoot", element
                    )
                except Exception:
                    time.sleep(2)
                    shadow_root = self.execute_script(
                        "return arguments[0].shadowRoot", element
                    )
            if timeout == 0.1 and not shadow_root:
                raise Exception(
                    "Element {%s} has no shadow root!" % selector_chain
                )
            elif not shadow_root:
                time.sleep(2)  # Wait two seconds for the shadow root to appear
                shadow_root = self.execute_script(
                    "return arguments[0].shadowRoot", element
                )
                if not shadow_root:
                    raise Exception(
                        "Element {%s} has no shadow root!" % selector_chain
                    )
            selector_chain += "::shadow "
            selector_chain += selector_part
            try:
                if (
                    selenium4
                    and self.is_chromium()
                    and int(self.__get_major_browser_version()) >= 96
                ):
                    if timeout == 0.1:
                        element = shadow_root.find_element(
                            By.CSS_SELECTOR, value=selector_part)
                    else:
                        found = False
                        for i in range(int(timeout) * 4):
                            try:
                                element = shadow_root.find_element(
                                    By.CSS_SELECTOR, value=selector_part)
                                is_present = True
                                if must_be_visible:
                                    if not element.is_displayed():
                                        raise Exception(
                                            "Shadow Root element not visible!")
                                found = True
                                break
                            except Exception:
                                time.sleep(0.2)
                                continue
                        if not found:
                            element = shadow_root.find_element(
                                By.CSS_SELECTOR, value=selector_part)
                            is_present = True
                            if must_be_visible and not element.is_displayed():
                                raise Exception(
                                    "Shadow Root element not visible!")
                else:
                    element = page_actions.wait_for_element_present(
                        shadow_root,
                        selector_part,
                        by=By.CSS_SELECTOR,
                        timeout=timeout,
                    )
            except Exception:
                error = "not present"
                the_exception = "NoSuchElementException"
                if must_be_visible and is_present:
                    error = "not visible"
                    the_exception = "ElementNotVisibleException"
                msg = (
                    "Shadow DOM Element {%s} was %s after %s seconds!"
                    % (selector_chain, error, timeout)
                )
                page_actions.timeout_exception(the_exception, msg)
        return element



    def get_shadow_text(self, selector, timeout):
        element = self.__get_shadow_element(
            selector, timeout=timeout, must_be_visible=True
        )
        element_text = element.text
        if self.browser == "safari":
            element_text = element.get_attribute("innerText")
        return element_text


        def __fail_if_invalid_shadow_selector_usage(self, selector):
            if selector.strip().endswith("::shadow"):
                msg = (
                    "A Shadow DOM selector cannot end on a shadow root element!"
                    " End the selector with an element inside the shadow root!"
                )
                raise Exception(msg)



    def shadow_click(self, selector, timeout):
        element = get_shadow_element(
            selector, timeout=timeout, must_be_visible=True
        )
        element.click()

    def shadow_type(self, selector, text, timeout, clear_first=True):
        element = self.__get_shadow_element(
            selector, timeout=timeout, must_be_visible=True
        )
        if clear_first:
            try:
                element.clear()
                backspaces = Keys.BACK_SPACE * 42  # Autofill Defense
                element.send_keys(backspaces)
            except Exception:
                pass
        if type(text) is int or type(text) is float:
            text = str(text)
        if not text.endswith("\n"):
            element.send_keys(text)
            if settings.WAIT_FOR_RSC_ON_PAGE_LOADS:
                self.wait_for_ready_state_complete()
        else:
            element.send_keys(text[:-1])
            element.send_keys(Keys.RETURN)
            if settings.WAIT_FOR_RSC_ON_PAGE_LOADS:
                self.wait_for_ready_state_complete()

    def shadow_clear(
            self,
            selector: str = Field(default="", strict=True, min_length=1),
            timeout: int = constants.SMALL_TIMEOUT
    ):
        element = self._get_shadow_element(selector, timeout=timeout, must_be_visible=True)
        try:
            element.clear()
            backspaces = Keys.BACK_SPACE * 42  # Autofill Defense
            element.send_keys(backspaces)
        except WebDriverException:
            pass
