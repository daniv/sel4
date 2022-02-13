"""
https://saucelabs.com/selenium-4
"""
from typing import Optional, List, Dict

from pydantic import HttpUrl
from selenium.common.exceptions import (
    NoSuchWindowException,
    WebDriverException
)
from selenium.webdriver.remote.webdriver import WebDriver

from .basetest import BasePytestUnitTestCase
from .exceptions import OutOfScopeException

from selenium.webdriver.common.by import By
from typing_extensions import Literal

from ..utils.typeutils import NoneStr
from sel4.conf import settings

SeleniumBy = Literal[
    By.ID, By.XPATH, By.LINK_TEXT, By.PARTIAL_LINK_TEXT, By.NAME, By.TAG_NAME, By.CLASS_NAME, By.CSS_SELECTOR
]


class WebDriverTest(BasePytestUnitTestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.browser_name: NoneStr = None
        # self.driver: Optional[WebDriver] = None
        # self.slow_mode: bool = False
        # self.demo_mode: bool = False
        # self.xvfb: bool = False
        # self.headed: bool = False
        # self.headless: bool = False

        self._headless_active = False
        self._reuse_session: bool = False
        self._default_driver: Optional[WebDriver] = None
        self._drivers_list: List[WebDriver] = []
        # self._enable_ws = False
        self._use_grid = False

        self.__driver_browser_map: Dict[WebDriver, str] = {}
        self.__last_page_load_url: Optional[HttpUrl] = None

    def __check_scope__(self):
        if self.browser_name:
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
        # self._headless_active = False
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

        if self.config.getoption("servername", None):
            if self.config.getoption("servername") != "localhost":
                self._use_grid = True

        if self.config.getoption("with_db_reporting", False):
            pass

        if self.config.getoption("headless", False) or self.config.getoption("xvfb", False):
            width = settings.HEADLESS_START_WIDTH
            height = settings.HEADLESS_START_HEIGHT

        if self.config.getoption("device_metrics", False):
            ...

        if self.config.getoption("mobile_emulator", False):
            ...

        if self.config.getoption("dashboard", False):
            ...




