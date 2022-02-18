"""
https://saucelabs.com/selenium-4
"""
import pathlib
import re
import time
from typing import Dict, List, Optional

from dictor import dictor
from loguru import logger
from pydantic import (
    HttpUrl,
    ValidationError,
    validate_arguments,
    Field
)
from selenium.common.exceptions import (
    NoSuchWindowException,
    JavascriptException,
    StaleElementReferenceException,
    MoveTargetOutOfBoundsException,
    ElementNotInteractableException,
    WebDriverException
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from sel4.conf import settings
from sel4.core.helpers.js_utils import (
    wait_for_ready_state_complete,
    get_scroll_distance_to_element,
    wait_for_angularjs,
    is_in_frame,
    slow_scroll_to_element,
    scroll_to_element,
    js_click,
    jquery_click,
    jquery_slow_scroll_to
)
from sel4.core.helpers.page_actions import (
    switch_to_window,
    is_element_present,
    is_element_visible,
    is_element_enabled
)
from sel4.core.helpers.shadow import (
    is_shadow_selector,
    wait_for_shadow_element_visible,
    wait_for_shadow_element_present,
    shadow_click
)
from sel4.core.helpers.shared import SeleniumBy
from sel4.core.helpers.shared import (
    check_if_time_limit_exceeded,
    escape_quotes_if_needed
)
from sel4.core.plugins._webdriver_builder import WebDriverBrowserLauncher, get_driver
from . import constants
from .basetest import BasePytestUnitTestCase
from .exceptions import OutOfScopeException
from .helpers.demo_mode import (
    demo_mode_pause_if_active
)
from .helpers.driver import (
    open_url
)
from .helpers.element_actions import (
    wait_for_element_present,
    wait_for_link_text_present,
    wait_for_element_visible,
    wait_for_element_interactable,
    highlight_click,
    highlight_update_text
)
from .runtime import runtime_store, shared_driver, time_limit
from ..utils.typeutils import OptionalInt, NoneStr


class WebDriverTest(BasePytestUnitTestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # browser_name = StashKey[str]()
        # self.stash[browser_name] = self.config.getini("browser_name")
        self.driver: Optional[WebDriver] = None

        # self.slow_mode: bool = False
        # self.demo_mode: bool = False
        # self.xvfb: bool = False
        # self.headed: bool = False
        # self.headless: bool = False

        self._headless_active = False
        self._reuse_session: bool = False
        self._default_driver: Optional[WebDriver] = None
        self._drivers_list: List[WebDriver] = []
        self._enable_ws = False
        self._use_grid = False

        self.__driver_browser_map: Dict[WebDriver, str] = {}
        self.__last_page_load_url: Optional[str] = None

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

    def __ad_block_as_needed(self):
        """
        This is an internal method for handling ad-blocking.
        Use "pytest --ad-block" to enable this during tests.
        When not Chromium or in headless mode, use the hack.
        """
        ad_block_on = self.config.getoption("ad_block_on", False)
        headless = self.config.getoption("headless", False)

        if ad_block_on and (headless or not self.is_chromium()):
            # -- Chromium browsers in headed mode use the extension instead
            current_url, httpx_url = self.get_current_url()
            if not current_url == self.__last_page_load_url:
                if is_element_present(self.driver, By.CSS_SELECTOR, "iframe"):
                    self.ad_block()
                self.__last_page_load_url = current_url

    def __highlight_with_jquery(self, selector, loops, o_bs):
        self.wait_for_ready_state_complete()
        highlight_with_jquery(self.driver, selector, loops, o_bs)


    # def __make_css_match_first_element_only(self, selector):
    #     logger.trace("Only get the first match of -> {}", selector)
    #     return make_css_match_first_element_only(selector)

    # def __demo_mode_pause_if_active(self, tiny=False):
    #     if self.config.getoption("demo_mode", False):
    #         wait_time = settings.DEFAULT_DEMO_MODE_TIMEOUT
    #         if self.config.getoption("demo_sleep", None):
    #             wait_time = float(self.config.getoption("demo_sleep"))
    #         if not tiny:
    #             time.sleep(wait_time)
    #         else:
    #             time.sleep(wait_time / 3.4)
    #     elif self.config.getoption("slow_mode", False):
    #         self.__slow_mode_pause_if_active()

    # def __slow_mode_pause_if_active(self):
    #     if self.config.getoption("slow_mode", False):
    #         wait_time = settings.DEFAULT_DEMO_MODE_TIMEOUT
    #         if self.config.getoption("demo_mode", False):
    #             wait_time = float(self.config.getoption("demo_sleep"))
    #         time.sleep(wait_time)

    # def __demo_mode_scroll_if_active(self, how: SeleniumBy, selector: str):
    #     if self.config.getoption("demo_mode", False):
    #         self.slow_scroll_to(how, selector)
    #
    # def __demo_mode_highlight_if_active(self, how: SeleniumBy, selector: str):
    #     if self.config.getoption("demo_mode", False):
    #         self.highlight(how, selector)
    #     if self.config.getoption("slow_mode", False):
    #         time.sleep(0.08)
    #         element = self.wait_for_element_visible(how, selector, timeout=constants.SMALL_TIMEOUT)
    #         try:
    #             scroll_distance = get_scroll_distance_to_element(self.driver, element)
    #             if abs(scroll_distance) > settings.SSMD:
    #                 jquery_slow_scroll_to(how, selector)
    #             else:
    #                 self.__slow_scroll_to_element(element)
    #         except (StaleElementReferenceException, ElementNotInteractableException):
    #             self.wait_for_ready_state_complete()
    #             time.sleep(0.12)
    #             element = self.wait_for_element_visible(how, selector, constants.SMALL_TIMEOUT)
    #             self.__slow_scroll_to_element(element)
    #         time.sleep(0.12)

    def __quit_all_drivers(self):
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

    def __is_in_frame(self):
        return is_in_frame(self.driver)

    def is_chromium(self):
        """Return True if the browser is Chrome, Edge, or Opera."""
        self.__check_scope__()
        chromium = False
        browser_name = self.driver.capabilities["browserName"]
        if browser_name.lower() in ("chrome", "edge", "msedge", "opera"):
            chromium = True
        return chromium

    def ad_block(self):
        """Block ads that appear on the current web page."""
        ...

    def set_time_limit(self, time_limit: OptionalInt = None):
        self.__check_scope__()
        super(WebDriverTest, self).set_time_limit(time_limit)

    def sleep(self, seconds):
        self.__check_scope__()
        limit = runtime_store.get(time_limit, None)
        if limit:
            time.sleep(seconds)
        elif seconds < 0.4:
            check_if_time_limit_exceeded()
            time.sleep(seconds)
            check_if_time_limit_exceeded()
        else:
            start_ms = time.time() * 1000.0
            stop_ms = start_ms + (seconds * 1000.0)
            for x in range(int(seconds * 5)):
                check_if_time_limit_exceeded()
                now_ms = time.time() * 1000.0
                if now_ms >= stop_ms:
                    break
                time.sleep(0.2)

    def teardown(self) -> None:
        self.__quit_all_drivers()
        super().teardown()

    def setup(self) -> None:
        super(WebDriverTest, self).setup()

        if self._called_setup:
            return

        # self.addfinalizer(self._generate_driver_logs)
        self._called_setup = True
        self._called_teardown = False
        # self.slow_mode = self.config.getoption("slow_mode", False)
        # self.demo_mode = self.config.getoption("demo_mode", False)
        # self.demo_sleep = sb_config.demo_sleep
        # self.highlights = sb_config.highlights
        # self.time_limit = sb_config._time_limit
        # sb_config.time_limit = sb_config._time_limit  # Reset between tests
        # self.environment = sb_config.environment
        # self.env = self.environment  # Add a shortened version
        # self.with_selenium = sb_config.with_selenium  # Should be True
        # self.headless = self.config.getoption("headless", False)
        self._headless_active = False
        # self.headed = self.config.getoption("headed", False)
        # self.xvfb = self.config.getoption("xvfb", False)
        # self.interval = sb_config.interval
        # self.start_page = sb_config.start_page
        # self.with_testing_base = sb_config.with_testing_base
        # self.with_basic_test_info = sb_config.with_basic_test_info
        # self.with_screen_shots = sb_config.with_screen_shots
        # self.with_page_source = sb_config.with_page_source
        # self.with_db_reporting = sb_config.with_db_reporting
        # self.with_s3_logging = sb_config.with_s3_logging
        # self.protocol = sb_config.protocol
        # self.servername = sb_config.servername
        # self.port = sb_config.port
        # self.proxy_string = sb_config.proxy_string
        # self.proxy_bypass_list = sb_config.proxy_bypass_list
        # self.user_agent = sb_config.user_agent
        # self.mobile_emulator = sb_config.mobile_emulator
        # self.device_metrics = sb_config.device_metrics
        # self.cap_file = sb_config.cap_file
        # self.cap_string = sb_config.cap_string
        # self.settings_file = sb_config.settings_file
        # self.database_env = sb_config.database_env
        # self.message_duration = sb_config.message_duration
        # self.js_checking_on = sb_config.js_checking_on
        # self.ad_block_on = sb_config.ad_block_on
        # self.block_images = sb_config.block_images
        # self.chromium_arg = sb_config.chromium_arg
        # self.firefox_arg = sb_config.firefox_arg
        # self.firefox_pref = sb_config.firefox_pref
        # self.verify_delay = sb_config.verify_delay
        # self.disable_csp = sb_config.disable_csp
        # self.disable_ws = sb_config.disable_ws
        # self.enable_ws = sb_config.enable_ws

        if not self.config.getoption("disable_ws", False):
            self._enable_ws = True

        # self.swiftshader = sb_config.swiftshader
        # self.user_data_dir = sb_config.user_data_dir
        # self.extension_zip = sb_config.extension_zip
        # self.extension_dir = sb_config.extension_dir
        # self.external_pdf = sb_config.external_pdf
        # self.maximize_option = sb_config.maximize_option
        # self.save_screenshot_after_test = sb_config.save_screenshot
        # self.visual_baseline = sb_config.visual_baseline
        # self.timeout_multiplier = sb_config.timeout_multiplier
        # self.pytest_html_report = sb_config.pytest_html_report
        # self.report_on = False
        # if self.pytest_html_report:
        #     self.report_on = True

        if self.config.getoption("servername", None):
            if self.config.getoption("servername") != "localhost":
                self._use_grid = True

        if self.config.getoption("with_db_reporting", False):
            pass

        headless = self.config.getoption("headless", False)
        xvfb = self.config.getoption("xvfb", False)
        if headless or xvfb:
            ...

        from sel4.core.runtime import start_time_ms, timeout_changed

        if runtime_store.get(timeout_changed, False):
            ...

        if self.config.getoption("device_metrics", False):
            ...

        if self.config.getoption("mobile_emulator", False):
            ...

        if self.config.getoption("dashboard", False):
            ...

        from sel4.core.runtime import shared_driver

        has_url = False
        if self._reuse_session:
            if runtime_store.get(shared_driver, None):
                try:
                    self._default_driver = runtime_store.get(shared_driver, None)
                    self.driver: WebDriver = runtime_store.get(shared_driver, None)
                    self._drivers_list = [self.driver]
                    url, httpx_url = self.get_current_url()
                    if url is not None:
                        has_url = True
                    if len(self.driver.window_handles) > 1:
                        while len(self.driver.window_handles) > 1:
                            self.switch_to_window(len(self.driver.window_handles) - 1)
                            self.driver.close()

                        self.switch_to_window(0)
                    if self.config.getoption("crumbs", False):
                        self.driver.delete_all_cookies()
                except WebDriverException:
                    pass
        if self._reuse_session and runtime_store.get(shared_driver, None) and has_url:
            start_page = False
            if self.config.getoption("start_page", None):
                HttpUrl.validate(self.config.getoption("start_page"))
                start_page = True
                self.open(self.config.getoption("start_page"))
        else:
            try:
                browser_launcher = WebDriverBrowserLauncher(
                    browser_name=self.config.getini("browser_name"),
                    headless=self.config.getoption("headless"),
                    enable_sync=self.config.getoption("enable_sync", False),
                    use_grid=self._use_grid,
                    block_images=self.config.getoption("block_images", False),
                    external_pdf=self.config.getoption("external_pdf", False),
                    mobile_emulator=self.config.getoption("mobile_emulator", False),
                    user_agent=self.config.getoption("user_agent", None),
                    proxy_auth=self.config.getoption("proxy_auth", None),
                    disable_csp=self.config.getoption("disable_csp", False),
                    ad_block_on=self.config.getoption("ad_block_on", False),
                    devtools=self.config.getoption("devtools", False),
                    incognito=self.config.getoption("incognito", False),
                    guest_mode=self.config.getoption("guest_mode", False),
                    extension_zip=self.config.getoption("extension_zip", []),
                    extension_dir=self.config.getoption("extension_dir", None),
                    user_data_dir=self.config.getoption("user_data_dir", None),
                    servername=self.config.getoption("servername", None),
                    use_auto_ext=self.config.getoption("use_auto_ext", False),
                    proxy_string=self.config.getoption("proxy_string", None),
                    enable_ws=self.config.getoption("enable_ws", False),
                    remote_debug=self.config.getoption("remote_debug", False),
                    swiftshader=self.config.getoption("swiftshader", False),
                    chromium_arg=self.config.getoption("chromium_arg", []),
                )
            except ValidationError as e:
                logger.exception("Failed to validate WebDriverBrowserLauncher", e)
                raise e
            self.driver = self.get_new_driver(browser_launcher, switch_to=True)
            self._default_driver = self.driver
            if self._reuse_session:
                runtime_store[shared_driver] = self.driver

            if self.config.getini("browser_name") in ["firefox", "safari"]:
                self.config.option.mobile_emulator = False

            self.set_time_limit(self.config.getoption("time_limit", None))
            runtime_store[start_time_ms] = int(time.time() * 1000.0)
            if not self._start_time_ms:
                # Call this once in case of multiple setUp() calls in the same test
                self._start_time_ms = runtime_store[start_time_ms]

    # region WebDriver Actions

    def get_page_source(self) -> str:
        self.wait_for_ready_state_complete()
        logger.debug("Returning current page source")
        return self.driver.page_source

    def get_current_url(self) -> str:
        self.__check_scope__()
        current_url = self.driver.current_url
        logger.debug("Gets the current page url -> {}", current_url)
        return current_url

    def open(self, url: str) -> None:
        """
        Navigates the current browser window to the specified page.

        :param url: the url to navigate to
        """
        self.__check_scope__()
        self.__check_browser__()
        pre_action_url = self.driver.current_url
        try:
            _method = "selenium.webdriver.chrome.webdriver.get()"
            logger.debug("Navigate to {url} using [inspect.class]{method}[/]", url=url, method=_method)
            open_url(self.driver, url, tries=2)
        except WebDriverException as e:
            # TODO: ExceptionFormatter
            logger.exception("Could not open url: {url}", url=url)
            e.__logged__ = True
            raise e
        if self.driver.current_url == pre_action_url and pre_action_url != url:
            time.sleep(0.1)
        if settings.WAIT_FOR_RSC_ON_PAGE_LOADS:
            self.wait_for_ready_state_complete()
        demo_mode_pause_if_active()

    def open_new_window(self, switch_to=True):
        """ Opens a new browser tab/window and switches to it by default. """
        logger.debug("Open a new browser window and switch to it -> {}", switch_to)
        self.__check_scope__()
        self.driver.execute_script("window.open('');")
        time.sleep(0.01)
        if switch_to:
            self.switch_to_newest_window()
            time.sleep(0.01)
            if self.driver.capabilities.get("browserName") == "safari":
                self.wait_for_ready_state_complete()

    @validate_arguments
    def switch_to_window(self, window: int | str, timeout: OptionalInt) -> None:
        """
        Switches control of the browser to the specified window.

        :param window: The window index or the window name
        :param timeout: optiona timeout
        """
        logger.debug(" Switches control of the browser to the specified window -> ", window)
        self.__check_scope__()
        timeout = self.get_timeout(timeout, constants.SMALL_TIMEOUT)
        switch_to_window(self.driver, window, timeout)

    def switch_to_default_window(self) -> None:
        self.switch_to_window(0)

    def switch_to_default_driver(self):
        """Sets driver to the default/original driver."""
        self.__check_scope__()
        self.driver = self._default_driver
        if self.driver in self.__driver_browser_map:
            getattr(self.config, "_inicache")["browser_name"] = self.__driver_browser_map[self.driver]
        self.bring_active_window_to_front()

    def switch_to_newest_window(self):
        self.switch_to_window(len(self.driver.window_handles) - 1)

    def get_new_driver(self, launcher_data: WebDriverBrowserLauncher, switch_to=True):
        self.__check_scope__()
        browser = self.config.getini("browser_name")
        if browser == "remote" and self.config.getoption("servername", "") == "localhost":
            raise RuntimeError(
                'Cannot use "remote" browser driver on localhost!'
                " Did you mean to connect to a remote Grid server"
                " such as BrowserStack or Sauce Labs? In that"
                ' case, you must specify the "server" and "port"'
                " parameters on the command line! "
            )
        cap_file = self.config.getoption("cap_file", None)
        cap_string = self.config.getoption("cap_string", None)
        if browser == "remote" and not (cap_file or cap_string):
            browserstack_ref = "https://browserstack.com/automate/capabilities"
            sauce_labs_ref = "https://wiki.saucelabs.com/display/DOCS/Platform+Configurator#/"
            raise RuntimeError(
                "Need to specify a desired capabilities file when "
                'using "--browser remote". Add "--cap_file FILE". '
                "File should be in the Python format"
                "%s OR "
                "%s "
                "See SeleniumBase/examples/sample_cap_file_BS.py "
                "and SeleniumBase/examples/sample_cap_file_SL.py" % (browserstack_ref, sauce_labs_ref)
            )

        new_driver = get_driver(launcher_data)
        self._drivers_list.append(new_driver)
        self.__driver_browser_map[new_driver] = launcher_data.browser_name
        if switch_to:
            self.driver = new_driver
            browser_name = launcher_data.browser_name
            # TODO: change ini value
            if self.config.getoption("headless", False) or self.config.getoption("xvfb", False):
                width = settings.HEADLESS_START_WIDTH
                height = settings.HEADLESS_START_HEIGH
                self.driver.set_window_size(width, height)
                self.wait_for_ready_state_complete()
            else:
                browser_name = self.driver.capabilities.get("browserName").lower()
                if browser_name == "chrome" or browser_name == "edge":
                    width = settings.CHROME_START_WIDTH
                    height = settings.CHROME_START_HEIGHT
                    if self.config.getoption("maximize_option", False):
                        self.driver.maximize_window()
                    elif self.config.getoption("fullscreen_option", False):
                        self.driver.fullscreen_window()
                    else:
                        self.driver.set_window_size(width, height)
                    self.wait_for_ready_state_complete()
                elif browser_name == "firefox":
                    width = settings.CHROME_START_WIDTH
                    if self.config.getoption("maximize_option", False):
                        self.driver.maximize_window()
                    else:
                        self.driver.set_window_size(width, 720)
                    self.wait_for_ready_state_complete()
                elif browser_name == "safari":
                    width = settings.CHROME_START_WIDTH
                    if self.config.getoption("maximize_option", False):
                        self.driver.maximize_window()
                        self.wait_for_ready_state_complete()
                    else:
                        self.driver.set_window_rect(10, 30, width, 630)
            if self.config.getoption("start_page", None):
                self.open(self.config.getoption("start_page"))
            return new_driver

    @validate_arguments
    def wait_for_ready_state_complete(self, timeout: OptionalInt = None):
        """Waits for the "readyState" of the page to be "complete".
        Returns True when the method completes.
        """
        self.__check_scope__()
        self.__check_browser__()
        timeout = self.get_timeout(timeout, constants.EXTREME_TIMEOUT)
        wait_for_ready_state_complete(self.driver, timeout)
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
        wait_for_angularjs(self.driver, timeout, **kwargs)
        return True

    def bring_active_window_to_front(self):
        """Brings the active browser window to the front.
        This is useful when multiple drivers are being used."""
        self.__check_scope__()
        try:
            if not self.__is_in_frame():
                # Only bring the window to the front if not in a frame
                # because the driver resets itself to default content.
                logger.debug("Bring the window to the front, since is not in a frame")
                self.switch_to_window(self.driver.current_window_handle)
        except WebDriverException:
            pass

    def _generate_driver_logs(self, driver: WebDriver):
        from ..contrib.rich.consoles import get_html_console
        from ..contrib.rich.themes import DRACULA_TERMINAL_THEME
        from ..contrib.rich.html_formats import CONSOLE_HTML_FORMAT
        console = get_html_console()
        from time import localtime, strftime
        dc = dictor
        log_path: pathlib.Path = dict(settings.PROJECT_PATHS).get("LOGS")
        s_id = driver.session_id
        from rich.table import Table
        for log_type in driver.log_types:
            file_name_path = log_path.joinpath(f'{log_type}_{s_id}.html')
            table = Table(title="test table", caption="table caption", expand=False)
            logs = self.driver.get_log(log_type)
            for entry in logs:
                local = localtime(dc(entry, "timestamp"))
                table.add_row(
                    strftime(local, "X x"),
                    dc(entry, "level"),
                    dc(entry, "message"),
                    dc(entry, "source")
                )
            console.save_html(
                str(file_name_path),
                theme=DRACULA_TERMINAL_THEME,
                code_format=CONSOLE_HTML_FORMAT,
                clear=True
            )


    # endregion WebDriver Actions

    # region WebElement Actions

    def __scroll_to_element(self, element: WebElement, how: SeleniumBy, selector: str) -> None:
        success = scroll_to_element(self.driver, element)
        if not success and selector:
            self.wait_for_ready_state_complete()
            element = wait_for_element_visible(self.driver, how, selector, timeout=constants.SMALL_TIMEOUT)
        demo_mode_pause_if_active(tiny=True)

    def is_link_text_present(self, link_text: str):
        """
        Returns True if the link text appears in the HTML of the page.
        The element doesn't need to be visible,
        such as elements hidden inside a dropdown selection

        :param link_text: the text to search
        :return: rue if the link text appears in the HTML of the page
        """
        logger.debug("Determine if link text: \"{text}\" can be found on DOM", text=link_text)
        self.wait_for_ready_state_complete()
        soup = self.get_beautiful_soup(self.get_page_source())
        html_links = soup.find_all("a")
        for html_link in html_links:
            if html_link.text.strip() == link_text.strip():
                logger.debug("link text: {text} was located", text=link_text)
                return True
        logger.debug("link text: {text} was not located", text=link_text)
        return False

    def click_link_text(self, link_text: str, timeout: OptionalInt = None):
        self.__check_scope__()
        timeout = self.get_timeout(timeout, constants.SMALL_TIMEOUT)
        if self.driver.capabilities.get("browserName") == "safari":
            ...
        if not self.is_link_text_present(link_text):
            wait_for_link_text_present(self.driver, link_text, timeout=timeout)
        pre_action_url = self.get_current_url()
        try:
            element = self.wait_for_link_text_visible(link_text, timeout=0.2)
            self.__demo_mode_highlight_if_active(link_text, by=By.LINK_TEXT)
            try:
                element.click()
            except (StaleElementReferenceException, ElementNotInteractableException):
                self.wait_for_ready_state_complete()
                time.sleep(0.16)
                element = self.wait_for_link_text_visible(
                    link_text, timeout=timeout
                )
                element.click()
        except Exception:
            found_css = False
            text_id = self.get_link_attribute(link_text, "id", False)
            if text_id:
                link_css = '[id="%s"]' % link_text
                found_css = True

            if not found_css:
                href = self.__get_href_from_link_text(link_text, False)
                if href:
                    if href.startswith("/") or page_utils.is_valid_url(href):
                        link_css = '[href="%s"]' % href
                        found_css = True

            if not found_css:
                ngclick = self.get_link_attribute(link_text, "ng-click", False)
                if ngclick:
                    link_css = '[ng-click="%s"]' % ngclick
                    found_css = True

            if not found_css:
                onclick = self.get_link_attribute(link_text, "onclick", False)
                if onclick:
                    link_css = '[onclick="%s"]' % onclick
                    found_css = True

            success = False
            if found_css:
                if self.is_element_visible(link_css):
                    self.click(link_css)
                    success = True
                else:
                    # The link text might be hidden under a dropdown menu
                    success = self.__click_dropdown_link_text(
                        link_text, link_css
                    )

            if not success:
                element = self.wait_for_link_text_visible(
                    link_text, timeout=settings.MINI_TIMEOUT
                )
                element.click()

        if settings.WAIT_FOR_RSC_ON_CLICKS:
            self.wait_for_ready_state_complete()
        if self.config.getoption("demo_mode"):
            if self.driver.current_url != pre_action_url:
                demo_mode_pause_if_active()
            else:
                demo_mode_pause_if_active(tiny=True)
        elif self.config.getoption("slow_mode"):
            self._slow_mode_pause_if_active()

    def click_partial_link_text(self, partial_link_text: str, timeout: OptionalInt = None):
        ...

    def is_link_text_visible(self, link_text):
        self.wait_for_ready_state_complete()
        time.sleep(0.01)
        return is_element_visible(self.driver, By.LINK_TEXT, link_text)

    def is_partial_link_text_visible(self, partial_link_text):
        self.wait_for_ready_state_complete()
        time.sleep(0.01)
        return is_element_visible(self.driver, By.PARTIAL_LINK_TEXT, partial_link_text)

    @validate_arguments
    def click(
            self,
            how: SeleniumBy,
            selector: str = Field(default="", strict=True, min_length=1),
            timeout: OptionalInt = None,
            delay: float = 0.0,
            scroll=True
    ) -> None:
        self.__check_scope__()
        logger.debug("Performing a click on {}:'{}'", how.upper(), selector)
        self.get_timeout(timeout, constants.SMALL_TIMEOUT)
        if delay and (type(delay) in [int, float]) and delay > 0:
            time.sleep(delay)
        if how == By.LINK_TEXT:
            if not self.is_link_text_visible(selector):
                # Handle a special case of links hidden in dropdowns
                self.click_link_text(selector, timeout=timeout)
                return
        if how == By.PARTIAL_LINK_TEXT:
            if not self.is_partial_link_text_visible(selector):
                # Handle a special case of partial links hidden in dropdowns
                self.click_partial_link_text(selector, timeout=timeout)
                return
        if is_shadow_selector(selector):
            shadow_click(self.driver, selector)
            return
        element = wait_for_element_interactable(self.driver, how, selector, timeout=timeout)
        demo_mode_highlight_if_active(self.driver, how, selector)
        demo_mode = self.config.getoption("demo_mode", False)
        slow_mode = self.config.getoption("slow_mode", False)
        if scroll and not demo_mode and not slow_mode:
            self.__scroll_to_element(element, how, selector)
        pre_action_url = self.driver.current_url

        def handle_anchor():
            # Handle a special case of opening a new tab (headless)
            try:
                href = element.get_attribute("href").strip()
                onclick = element.get_attribute("onclick")
                target = element.get_attribute("target")
                new_tab = False
                if target == "_blank":
                    _new_tab = True
                if new_tab and self.__looks_like_a_page_url(href):
                    if onclick:
                        try:
                            self.execute_script(onclick)
                        except WebDriverException | JavascriptException:
                            pass
                    current_window = self.driver.current_window_handle
                    self.open_new_window()
                    try:
                        self.open(href)
                    except WebDriverException:
                        pass
                    self.switch_to_window(current_window)
                    return
            except WebDriverException:
                pass

        def handle_safari():
            if how == By.LINK_TEXT:
                self.__jquery_click(how, selector)
            else:
                self.__js_click(how, selector)

        def retry_on_stale():
            nonlocal element
            element = wait_for_element_interactable(self.driver, how, selector, timeout=timeout)
            try:
                self.__scroll_to_element(element, how, selector)
            except WebDriverException:
                pass
            if self.driver.capabilities.get("browserName") == "safari":
                handle_safari()
            else:
                element.click()

        def retry_on_element_not_interactable():
            nonlocal element
            element = wait_for_element_interactable(self.driver, how, selector, timeout=timeout)
            if element.tag_name == "a":
                handle_anchor()
            self.__scroll_to_element(element, how, selector)
            if self.driver.capabilities.get("browserName") == "safari":
                handle_safari()
            else:
                element.click()

        def retry_move_target_or_wd():
            try:
                js_click(how, selector)
            except WebDriverException | JavascriptException:
                try:
                    jquery_click(how, selector)
                except WebDriverException | JavascriptException:
                    nonlocal element
                    element = wait_for_element_interactable(self.driver, how, selector, timeout=timeout)
                    element.click()

        try:
            if self.driver.capabilities.get("browserName") == "safari":
                handle_safari()
            else:
                try:
                    if self.config.getoption("headless") and element.tag_name == "a":
                        # Handle a special case of opening a new tab (headless)
                        handle_anchor()
                except WebDriverException:
                    pass
                # Normal click
                logger.debug("Executing normal webelement click")
                element.click()
        except StaleElementReferenceException:
            logger.debug("Recovering from StaleElementReferenceException")
            self.wait_for_ready_state_complete()
            time.sleep(0.16)
            retry_on_stale()

        except ElementNotInteractableException:
            logger.debug("Recovering from ElementNotInteractableException")
            self.wait_for_ready_state_complete()
            time.sleep(0.1)
            retry_on_element_not_interactable()

        except WebDriverException | MoveTargetOutOfBoundsException as e:
            logger.debug("Recovering from {e_type}", e_type=e.__class__.__name__)
            self.wait_for_ready_state_complete()
            retry_move_target_or_wd()

        if settings.WAIT_FOR_RSC_ON_CLICKS:
            self.wait_for_ready_state_complete()
        if demo_mode:
            if self.driver.current_url != pre_action_url:
                demo_mode_pause_if_active()
            else:
                demo_mode_pause_if_active(tiny=True)
        elif slow_mode:
            self._slow_mode_pause_if_active()

    def slow_click(
            self,
            how: SeleniumBy,
            selector: str = Field(default="", strict=True, min_length=1),
            timeout: OptionalInt = None,
    ) -> None:
        """
        Similar to click(), but pauses for a brief moment before clicking.
        When used in combination with setting the user-agent, it can often
        bypass bot-detection by tricking websites into thinking that you're
        not a bot. (Useful on websites that block web automation tools.)
        Here's an example message from GitHub's bot-blocker:
        ``You have triggered an abuse detection mechanism...``

        :param how: the type of selector being used
        :param selector: the locator for identifying the page element (required)
        :param timeout: the time to wait for the element in seconds
        """
        self.__check_scope__()
        logger.debug("Performing a slow click on {}:'{}'", how.upper(), selector)
        timeout = self.get_timeout(timeout, constants.SMALL_TIMEOUT)
        demo_mode = self.config.getoption("demo_mode", False)
        slow_mode = self.config.getoption("slow_mode", False)
        if not demo_mode and not slow_mode:
            self.click(how, selector, timeout=timeout, delay=1.05)
        elif slow_mode:
            self.click(how, selector, timeout=timeout, delay=0.65)
        else:
            self.click(how, selector, timeout=timeout, delay=0.25)

    def double_click(
            self,
            how: SeleniumBy,
            selector: str = Field(default="", strict=True, min_length=1),
            timeout: OptionalInt = None,
    ) -> None:
        self.__check_scope__()
        logger.debug("Performing a double-click on {}:'{}'", how.upper(), selector)
        timeout = self.get_timeout(timeout, constants.SMALL_TIMEOUT)
        element = wait_for_element_interactable(self.driver, how, selector, timeout)

    @validate_arguments
    def slow_scroll_to(
            self,
            how: SeleniumBy,
            selector: str = Field(default="", strict=True, min_length=1),
            timeout: OptionalInt = None
    ):
        """ Slow motion scroll to destination """
        self.__check_scope__()
        timeout = self.get_timeout(timeout, constants.SMALL_TIMEOUT)
        element = self.wait_for_element_visible(how, selector, timeout)
        try:
            scroll_distance = get_scroll_distance_to_element(
                self.driver, element
            )
            if abs(scroll_distance) > settings.SSMD:
                jquery_slow_scroll_to(how, selector)
            else:
                slow_scroll_to_element(element)
        except WebDriverException:
            self.wait_for_ready_state_complete()
            time.sleep(0.12)
            element = self.wait_for_element_visible(how, selector, timeout)
            slow_scroll_to_element(element)

    @validate_arguments
    def wait_for_element_visible(
            self,
            how: SeleniumBy,
            selector: str = Field(default="", strict=True, min_length=1),
            timeout: OptionalInt = None
    ):
        self.__check_scope__()
        timeout = self.get_timeout(timeout, constants.LARGE_TIMEOUT)
        if is_shadow_selector(selector):
            return wait_for_shadow_element_visible(self.driver, selector, timeout)
        return wait_for_element_visible(self.driver, how, selector, timeout)

    def wait_for_link_text_visible(self, link_text, timeout=None) -> WebElement:
        self.__check_scope__()
        timeout = self.get_timeout(timeout, constants.LARGE_TIMEOUT)
        return self.wait_for_element_visible(By.LINK_TEXT, link_text, timeout=timeout)

    def wait_for_element_present(
            self,
            how: SeleniumBy,
            selector: str = Field(default="", strict=True, min_length=1),
            timeout: OptionalInt = None
    ):
        """Waits for an element to appear in the HTML of a page.
        The element does not need be visible (it may be hidden)."""
        self.__check_scope__()
        timeout = self.get_timeout(timeout, constants.LARGE_TIMEOUT)
        if is_shadow_selector(selector):
            return wait_for_shadow_element_present(self.driver, selector, timeout)
        return wait_for_element_present(self.driver, how, selector, timeout)

    def get_link_attribute(self, link_text: str, attribute: str, hard_fail=True):
        """
        Finds a link by link text and then returns the attribute's value.
        If the link text or attribute cannot be found, an exception will
        get raised if hard_fail is True (otherwise None is returned).

        :param link_text: The link test to find
        :param attribute: the attribute name
        :param hard_fail:
        :return:
        """
        self.wait_for_ready_state_complete()
        soup = self.get_beautiful_soup(self.get_page_source())
        logger.trace("Searching for anchor using BeautifulSoup")
        html_links = soup.find_all("a")
        logger.trace("Found {count} anchors on current html source page", count=len(html_links))
        for html_link in html_links:
            if html_link.text.strip() == link_text.strip():
                if html_link.has_attr(attribute):
                    attribute_value = html_link.get(attribute)
                    return attribute_value
                if hard_fail:
                    raise WebDriverException(f"Unable to find attribute {attribute} from link text {link_text}!")
                else:
                    return None
            if hard_fail:
                raise WebDriverException("Link text {link_text} was not found!")
            else:
                return None

    @validate_arguments
    def is_element_visible(self, how: SeleniumBy, selector: str = Field(default="", strict=True, min_length=1)):
        self.wait_for_ready_state_complete()
        return is_element_visible(self.driver, how, selector)

    @validate_arguments
    def is_element_enabled(self, how: SeleniumBy, selector: str = Field(default="", strict=True, min_length=1)):
        self.wait_for_ready_state_complete()
        return is_element_enabled(self.driver, how, selector)

    # region highlight

    def highlight(
            self,
            how: SeleniumBy,
            selector: str = Field(..., strict=True, min_length=1),
            scroll=True
    ) -> None:
        self.__check_scope__()
        loops = settings.HIGHLIGHT_LOOPS
        element = wait_for_element_visible(self.driver, how, selector, constants.SMALL_TIMEOUT)
        if scroll:
            try:
                if self.driver.capabilities.get("browserName") == "safari":
                    ...
                else:
                    jquery_slow_scroll_to(self.driver, how, selector)
            except WebDriverException | JavascriptException as e:
                logger.warning('Exception while scrolling to element {how}:"{selector}"', str(e))
                self.wait_for_ready_state_complete()
                time.sleep(0.12)
                element = wait_for_element_visible(self.driver, how, selector, constants.SMALL_TIMEOUT)
                slow_scroll_to_element(element)

        selector = self.convert_to_css_selector(how, selector)
        if self.config.getoption("highlights", False):
            loops = self.config.getoption("highlights")
        loops = int(loops)
        style = element.get_attribute("style")
        if style:
            if "box-shadow: " in style:
                box_start = style.find("box-shadow: ")
                box_end = style.find(";", box_start) + 1
                original_box_shadow = style[box_start:box_end]
                o_bs = original_box_shadow
        selector = make_css_match_first_element_only(selector)
        selector = re.escape(selector)
        selector = escape_quotes_if_needed(selector)
        self.__highlight_with_jquery(selector, loops, o_bs)
        time.sleep(0.065)

    @validate_arguments
    def highlight_click(
            self,
            how: SeleniumBy,
            selector: str = Field(..., strict=True, min_length=1),
            scroll=True
    ) -> None:
        self.__check_scope__()
        if not self.config.getoption("demo_mode"):
            self.highlight(how, selector)
        self.click(how, selector, scroll)

    @validate_arguments
    def highlight_update_text(
            self,
            how: SeleniumBy,
            selector: str = Field(..., strict=True, min_length=1),
            text: NoneStr = None,
            scroll: bool = True
    ) -> None:
        """Highlights the element and then types text into the field."""
        if text is None:
            return
        self.__check_scope__()
        if not self.config.getoption("demo_mode"):
            self.highlight(how, selector, scroll=scroll)
        self.update_text(how, selector, text, scroll)

    # endregion highlight

    # endregion WebElement Actions

    # region JAVASCRIPT Actions

    # endregion JAVASCRIPT Actions

    # region JQUERY methods

    def execute_script(self, script: str = Field(min_length=5), *args):
        self.__check_scope__()
        self.__check_browser__()
        return self.driver.execute_script(script, *args)

    # endregion JQUERY methods




