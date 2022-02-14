"""
https://saucelabs.com/selenium-4
"""
import time
import webbrowser
from typing import Dict, List, Optional, Tuple

from httpx import URL
from loguru import logger
from pydantic import FileUrl, HttpUrl, ValidationError, validate_arguments
from selenium.common.exceptions import NoSuchWindowException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from sel4.conf import settings
from sel4.core.plugins._webdriver_builder import WebDriverBrowserLauncher, get_driver

from ..utils.typeutils import OptionalInt
from . import constants, js_utils, page_actions, shared
from .basetest import BasePytestUnitTestCase
from .exceptions import OutOfScopeException
from .runtime import runtime_store, shared_driver, time_limit


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
        self.__last_page_load_url: Optional[HttpUrl] = None

    def __check_scope__(self):
        if self.config.getoption("browser_name", None) is not None:
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
                if page_actions.is_element_present(self.driver, By.CSS_SELECTOR, "iframe"):
                    self.ad_block()
                self.__last_page_load_url = current_url

    def __demo_mode_pause_if_active(self, tiny=False):
        if self.config.getoption("demo_mode", False):
            wait_time = settings.DEFAULT_DEMO_MODE_TIMEOUT
            if self.config.getoption("demo_sleep", None):
                wait_time = float(self.config.getoption("demo_sleep"))
            if not tiny:
                time.sleep(wait_time)
            else:
                time.sleep(wait_time / 3.4)
        elif self.config.getoption("slow_mode", False):
            self.__slow_mode_pause_if_active()

    def __slow_mode_pause_if_active(self):
        if self.config.getoption("slow_mode", False):
            wait_time = settings.DEFAULT_DEMO_MODE_TIMEOUT
            if self.config.getoption("demo_mode", False):
                wait_time = float(self.config.getoption("demo_sleep"))
            time.sleep(wait_time)

    def __demo_mode_scroll_if_active(self, selector, by):
        if self.config.getoption("demo_mode", False):
            self.slow_scroll_to(selector, by=by)

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
                driver.quit()
            except AttributeError:
                pass
            except Exception:
                pass
        self.driver = None
        self._default_driver = None
        self._drivers_list = []

    def __is_in_frame(self):
        return js_utils.is_in_frame(self.driver)

    def is_chromium(self):
        """ Return True if the browser is Chrome, Edge, or Opera. """
        self.__check_scope__()
        chromium = False
        browser_name = self.driver.capabilities["browserName"]
        if browser_name.lower() in ("chrome", "edge", "msedge", "opera"):
            chromium = True
        return chromium

    def ad_block(self):
        """ Block ads that appear on the current web page. """
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
            shared.check_if_time_limit_exceeded()
            time.sleep(seconds)
            shared.check_if_time_limit_exceeded()
        else:
            start_ms = time.time() * 1000.0
            stop_ms = start_ms + (seconds * 1000.0)
            for x in range(int(seconds * 5)):
                shared.check_if_time_limit_exceeded()
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

    def get_current_url(self) -> Tuple[URL, str]:
        self.__check_scope__()
        current_url = self.driver.current_url
        return URL(current_url), current_url

    @validate_arguments
    def open(self, url: HttpUrl | FileUrl):
        """ Navigates the current browser window to the specified page. """
        self.__check_scope__()
        self.__check_browser__()
        pre_action_url, httpx_url = self.driver.current_url
        self.__last_page_load_url = None
        js_utils.clear_out_console_logs(self.driver)
        try:
            self.driver.get(url)
        except WebDriverException as e:
            if "ERR_CONNECTION_TIMED_OUT" in e.msg:
                self.sleep(0.5)
                self.driver.get(url)
            else:
                raise Exception(e.msg)
        if self.driver.current_url == pre_action_url and pre_action_url != url:
            time.sleep(0.1)
        if settings.WAIT_FOR_RSC_ON_PAGE_LOADS:
            self.wait_for_ready_state_complete()
        self.__demo_mode_pause_if_active()

    @validate_arguments
    def switch_to_window(self, window: int | str, timeout: OptionalInt) -> None:
        """
        Switches control of the browser to the specified window.

        :param window: The window index or the window name
        :param timeout: optiona timeout
        """
        self.__check_scope__()
        timeout = self.get_timeout(timeout, constants.SMALL_TIMEOUT)
        page_actions.switch_to_window(self.driver, window, timeout)

    def switch_to_default_window(self) -> None:
        self.switch_to_window(0)

    def switch_to_default_driver(self):
        """ Sets driver to the default/original driver. """
        self.__check_scope__()
        self.driver = self._default_driver
        if self.driver in self.__driver_browser_map:
            # TODO change init
            self.browser = self.__driver_browser_map[self.driver]
        self.bring_active_window_to_front()

    def switch_to_newest_window(self):
        self.switch_to_window(len(self.driver.window_handles) - 1)

    def get_new_driver(self, launcher_data: WebDriverBrowserLauncher, switch_to=True):
        self.__check_scope__()
        if self.config.get("browser_name") == "remote" and self.config.getoption("servername", "") == "localhost":
            raise RuntimeError(
                'Cannot use "remote" browser driver on localhost!'
                " Did you mean to connect to a remote Grid server"
                " such as BrowserStack or Sauce Labs? In that"
                ' case, you must specify the "server" and "port"'
                " parameters on the command line! "
            )
        cap_file = self.config.getoption("cap_file", None)
        cap_string = self.config.getoption("cap_string", None)
        if self.config.get("browser_name") == "remote" and not (cap_file or cap_string):
            browserstack_ref = "https://browserstack.com/automate/capabilities"
            sauce_labs_ref = "https://wiki.saucelabs.com/display/DOCS/Platform+Configurator#/"
            raise RuntimeError(
                "Need to specify a desired capabilities file when "
                'using "--browser remote". Add "--cap_file FILE". '
                "File should be in the Python format"
                "%s OR "
                "%s "
                "See SeleniumBase/examples/sample_cap_file_BS.py "
                "and SeleniumBase/examples/sample_cap_file_SL.py"
                % (browserstack_ref, sauce_labs_ref)
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
        """ Waits for the "readyState" of the page to be "complete".
            Returns True when the method completes.
        """
        self.__check_scope__()
        self.__check_browser__()
        timeout = self.get_timeout(timeout, constants.EXTREME_TIMEOUT)
        js_utils.wait_for_ready_state_complete(self.driver, timeout)
        self.wait_for_angularjs(timeout=settings.MINI_TIMEOUT)
        if self.js_checking_on:
            self.assert_no_js_errors()
        self.__ad_block_as_needed()
        return True

    def wait_for_angularjs(self, timeout: OptionalInt = None, **kwargs):
        """ Waits for Angular components of the page to finish loading.
        Returns True when the method completes.
        """
        self.__check_scope__()
        timeout = self.get_timeout(timeout, constants.MINI_TIMEOUT)
        js_utils.wait_for_angularjs(self.driver, timeout, **kwargs)
        return True

    def bring_active_window_to_front(self):
        """Brings the active browser window to the front.
        This is useful when multiple drivers are being used."""
        self.__check_scope__()
        try:
            if not self.__is_in_frame():
                # Only bring the window to the front if not in a frame
                # because the driver resets itself to default content.
                self.switch_to_window(self.driver.current_window_handle)
        except WebDriverException:
            pass

    # endregion WebDriver Actions


