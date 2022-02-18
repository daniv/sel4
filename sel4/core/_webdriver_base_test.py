import re
import time
from abc import ABC
from functools import cached_property
from typing import Optional, List, Dict, Any

import pytest
from loguru import logger
from pydantic import validate_arguments, Field
from selenium.common.exceptions import (
    WebDriverException,
    NoSuchWindowException
)
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By

from . import constants
from .basetest import PytestUnitTestCase
from .exceptions import OutOfScopeException
from .helpers__ import element_actions
from .helpers__ import js_utils
from .helpers__ import shared
from .runtime import runtime_store, shared_driver
from ..utils.typeutils import OptionalInt
from ..conf import settings


class NotUsingChromeException(WebDriverException):
    """Used by Chrome-only methods if not using Chrome"""
    pass


class WebDriverBaseTest(PytestUnitTestCase, ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.driver: Optional[WebDriver] = None
        self._reuse_session: bool = False
        self._default_driver: Optional[WebDriver] = None
        self._drivers_list: List[WebDriver] = []
        self.__driver_browser_map: Dict[WebDriver, str] = {}
        self.__last_page_load_url = "data:,"
        self.demo_mode = self.config.getoption("demo_mode", False)
        self.headless = self.config.getoption("headless")

    def __check_scope__(self):
        if self.config.getini("browser_name") is not None:
            return

        message = (
            "\n It looks like you are trying to call a WebDriverTest method"
            "\n from outside the scope of your test class's `self` object,"
            "\n which is initialized by calling WebDriverTest's setup() method."
            "\n The `self` object is where all test variables are defined."
            "\n When using page objects, be sure to pass the `self` object"
            "\n from your test class into your page object methods so that"
            "\n they can call BaseCase class methods with all the required"
            "\n variables, which are initialized during the setUp() method"
            "\n that runs automatically before all tests called by pytest."
        )
        raise OutOfScopeException(message)

    def __check_browser__(self):
        """
        Checks that the browser is not closed

        :raises: NoSuchWindowException if the window was already closed.
        """
        active_window = None
        try:
            active_window = self.driver.current_window_handle  # Fails if None
        except WebDriverException:
            pass
        if not active_window:
            raise NoSuchWindowException("Active window was already closed!")

    def sleep(self, seconds: float):
        self.__check_scope__()
        super(WebDriverBaseTest, self).sleep(seconds)

    def _clear_out_console_logs(self):
        try:
            logger.debug("Cleaning web-driver console logs before navigating to a new page...")
            for log_type in self.driver.log_types:
                self.driver.get_log(log_type)
        except WebDriverException:
            pass

    def _ad_block_as_needed(self):
        """ This is an internal method for handling ad-blocking.

        Use "pytest --ad-block" to enable this during tests.
        When not Chromium or in headless mode, use the hack.
        """
        ad_block_on = self.config.getoption("ad_block_on", False)
        if ad_block_on and (self.headless or not self.is_chromium()):
            current_url = self.get_current_url()
            if not current_url == self.__last_page_load_url:
                if element_actions.is_element_present(self.driver, By.CSS_SELECTOR, "iframe"):
                    self.ad_block()
                self.__last_page_load_url = current_url

    def __activate_html_inspector(self):
        self.wait_for_ready_state_complete()
        time.sleep(0.05)
        js_utils.activate_html_inspector(self.driver)

    @validate_arguments
    def _open_url(
            self,
            driver: WebDriver,
            url: str = Field(strict=True, min_length=4),
            tries: int = Field(default=2, ge=1)
    ):
        self._clear_out_console_logs()
        func = driver.get
        from ..utils.retries import retry_call
        retry_call(func, f_args=[url], tries=tries, backoff=2.0, delay=0.5, exceptions=WebDriverException)

    def activate_jquery(self):
        """If "jQuery is not defined", use this method to activate it for use.
        This happens because jQuery is not always defined on web sites."""
        self.wait_for_ready_state_complete()
        js_utils.activate_jquery(self.driver)
        self.wait_for_ready_state_complete()

    def get_current_url(self) -> str:
        self.__check_scope__()
        return self.driver.current_url

    def wait_for_ready_state_complete(self, timeout: OptionalInt = None):
        """Waits for the "readyState" of the page to be "complete".
        Returns True when the method completes.
        """
        self.__check_scope__()
        self.__check_browser__()
        timeout = self.get_timeout(timeout, constants.EXTREME_TIMEOUT)
        js_utils.wait_for_ready_state_complete(self.driver, timeout)
        self.wait_for_angularjs(timeout=constants.MINI_TIMEOUT)
        if self.config.getoption("js_checking_on"):
            self.assert_no_js_errors()
        self.__ad_block_as_needed()
        return True

    def wait_for_angularjs(self, timeout: OptionalInt = None, **kwargs):
        """Waits for Angular components of the page to finish loading.
        Returns True when the method completes.
        """
        self.__check_scope__()
        timeout = self.get_timeout(timeout, constants.MINI_TIMEOUT)
        js_utils.wait_for_angularjs(self.driver, timeout, **kwargs)
        return True

    def execute_script(self, script: str, *args) -> Any:
        self.__check_scope__()
        self.__check_browser__()
        return self.driver.execute_script(script, *args)

    def execute_async_script(self, script, timeout=None) -> Any:
        self.__check_scope__()
        self.__check_browser__()
        if not timeout:
            timeout = constants.EXTREME_TIMEOUT
        return js_utils.execute_async_script(self.driver, script, timeout)

    def safe_execute_script(self, script: str, *args):
        """When executing a script that contains a jQuery command,
        it's important that the jQuery library has been loaded first.
        This method will load jQuery if it wasn't already loaded."""
        self.__check_scope__()
        self.__check_browser__()
        if not js_utils.is_jquery_activated(self.driver):
            self.activate_jquery()
        return self.driver.execute_script(script, *args)

    def _demo_mode_pause_if_active(self, tiny=False):
        if self.demo_mode:
            wait_time = settings.DEFAULT_DEMO_MODE_TIMEOUT
            if self.config.getoption("demo_sleep", None):
                wait_time = float(self.config.getoption("demo_sleep"))
            if not tiny:
                time.sleep(wait_time)
            else:
                time.sleep(wait_time / 3.4)
        elif self.slow_mode:
            self._slow_mode_pause_if_active()

    @validate_arguments
    def load_html_string(self, html_string: str, new_page: bool = True):
        """Loads an HTML string into the web browser.
        If new_page==True, the page will switch to: "data:text/html,"
        If new_page==False, will load HTML into the current page."""
        self.__check_scope__()
        soup = self.get_beautiful_soup(html_string)
        found_base = False
        links = soup.findAll("link")
        href = None
        for link in links:
            if link.get("rel") == ["canonical"] and link.get("href"):
                found_base = True
                href = link.get("href")
                href = self.get_domain_url(href)
        if (
            found_base
            and html_string.count("<head>") == 1
            and html_string.count("<base") == 0
        ):
            html_string = html_string.replace(
                "<head>", '<head><base href="%s">' % href
            )
        elif not found_base:
            bases = soup.findAll("base")
            for base in bases:
                if base.get("href"):
                    href = base.get("href")
        if href:
            html_string = html_string.replace('base: "."', 'base: "%s"' % href)

        soup = self.get_beautiful_soup(html_string)
        scripts = soup.findAll("script")
        for script in scripts:
            if script.get("type") != "application/json":
                html_string = html_string.replace(str(script), "")
        soup = self.get_beautiful_soup(html_string)

        found_head = False
        found_body = False
        html_head = None
        html_body = None
        if soup.head and len(str(soup.head)) > 12:
            found_head = True
            html_head = str(soup.head)
            html_head = re.escape(html_head)
            html_head = shared.escape_quotes_if_needed(html_head)
            html_head = html_head.replace("\\ ", " ")
        if soup.body and len(str(soup.body)) > 12:
            found_body = True
            html_body = str(soup.body)
            html_body = html_body.replace("\xc2\xa0", "&#xA0;")
            html_body = html_body.replace("\xc2\xa1", "&#xA1;")
            html_body = html_body.replace("\xc2\xa9", "&#xA9;")
            html_body = html_body.replace("\xc2\xb7", "&#xB7;")
            html_body = html_body.replace("\xc2\xbf", "&#xBF;")
            html_body = html_body.replace("\xc3\x97", "&#xD7;")
            html_body = html_body.replace("\xc3\xb7", "&#xF7;")
            html_body = re.escape(html_body)
            html_body = shared.escape_quotes_if_needed(html_body)
            html_body = html_body.replace("\\ ", " ")
        html_string = re.escape(html_string)
        html_string = shared.escape_quotes_if_needed(html_string)
        html_string = html_string.replace("\\ ", " ")

        if new_page:
            self.open("data:text/html,")
        inner_head = """document.getElementsByTagName("head")[0].innerHTML"""
        inner_body = """document.getElementsByTagName("body")[0].innerHTML"""
        if not found_body:
            self.execute_script('''%s = \"%s\"''' % (inner_body, html_string))
        elif found_body and not found_head:
            self.execute_script('''%s = \"%s\"''' % (inner_body, html_body))
        elif found_body and found_head:
            self.execute_script('''%s = \"%s\"''' % (inner_head, html_head))
            self.execute_script('''%s = \"%s\"''' % (inner_body, html_body))
        else:
            raise Exception("Logic Error!")

        for script in scripts:
            js_code = script.string
            js_src = script.get("src")
            if js_code and script.get("type") != "application/json":
                js_code_lines = js_code.split("\n")
                new_lines = []
                for line in js_code_lines:
                    line = line.strip()
                    new_lines.append(line)
                js_code = "\n".join(new_lines)
                js_code = re.escape(js_code)
                js_utils.add_js_code(self.driver, js_code)
            elif js_src:
                js_utils.add_js_link(self.driver, js_src)
            else:
                pass

    def _quit_all_drivers(self):
        shared_drv = runtime_store.get(shared_driver, None)
        if self._reuse_session and shared_drv:
            if len(self._drivers_list) > 0:
                if self._drivers_list[0] != shared_drv:
                    if shared_drv in self._drivers_list:
                        self._drivers_list.remove(shared_drv)
                    self._drivers_list.insert(0, shared_drv)
                self._default_driver = self._drivers_list[0]
                self.switch_to_default_driver()
            if len(self._drivers_list) > 1:
                self._drivers_list = self._drivers_list[1:]
            else:
                self._drivers_list = []

        # Close all open browser windows
        self._drivers_list.reverse()  # Last In, First Out
        for driver in self._drivers_list:
            try:
                self.__generate_logs(driver)
                driver.quit()
            except AttributeError:
                pass
            except WebDriverException:
                pass
        self.driver = None
        self._default_driver = None
        self._drivers_list = []

    @property
    def is_chromium(self):
        """ Return True if the browser is Chrome, Edge, or Opera. """
        self.__check_scope__()
        chromium = False
        browser_name = self.driver.capabilities["browserName"]
        if browser_name.lower() in ("chrome", "edge", "msedge", "opera"):
            chromium = True
        return chromium

    @property
    def chrome_version(self) -> str:
        self.__check_scope__()
        self._fail_if_not_using_chrome("get_chrome_version()")
        driver_capabilities = self.driver.capabilities
        if "version" in driver_capabilities:
            chrome_version = driver_capabilities["version"]
        else:
            chrome_version = driver_capabilities["browserVersion"]
        return chrome_version

    @property
    def major_browser_version(self) -> str:
        try:
            version = self.driver.__dict__["caps"]["browserVersion"]
        except WebDriverException:
            try:
                version = self.driver.__dict__["caps"]["version"]
            except WebDriverException:
                version = str(
                    self.driver.__dict__["capabilities"]["version"]
                )
            self.driver.__dict__["caps"]["browserVersion"] = version
        major_browser_version = version.split(".")[0]
        return major_browser_version

    @property
    def chromedriver_version(self) -> str:
        self.__check_scope__()
        self._fail_if_not_using_chrome("get_chromedriver_version()")
        chrome_dict = self.driver.capabilities["chrome"]
        chromedriver_version = chrome_dict["chromedriverVersion"]
        chromedriver_version = chromedriver_version.split(" ")[0]
        return chromedriver_version

    def _fail_if_not_using_chrome(self, method):
        chrome = False
        browser_name = self.driver.capabilities["browserName"]
        if browser_name.lower() == "chrome":
            chrome = True
        if not chrome:
            message = (
                f'Error: "{method}" should only be called '
                'by tests running with self.browser == "chrome"! '
                'You should add an "if" statement to your code before calling '
                "this method if using browsers that are Not Chrome! "
                f'The browser detected was: "{browser_name}".'
            )
            pytest.fail(message)
            raise NotUsingChromeException(message)

    def block_ads(self):
        """ Same as self.ad_block() """
        self.ad_block()

    def ad_block(self):
        """ Block ads that appear on the current web page. """
        from seleniumbase.config import ad_block_list

        self.__check_scope()  # Using wait_for_RSC would cause an infinite loop
        for css_selector in ad_block_list.AD_BLOCK_LIST:
            css_selector = re.escape(css_selector)  # Add "\\" to special chars
            css_selector = self.__escape_quotes_if_needed(css_selector)
            script = (
                """var $elements = document.querySelectorAll('%s');
                var index = 0, length = $elements.length;
                for(; index < length; index++){
                $elements[index].remove();}"""
                % css_selector
            )
            try:
                self.execute_script(script)
            except Exception:
                pass  # Don't fail test if ad_blocking fails

