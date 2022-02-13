"""
https://saucelabs.com/selenium-4
"""
from typing import Optional

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

SeleniumBy = Literal[
    By.ID, By.XPATH, By.LINK_TEXT, By.PARTIAL_LINK_TEXT, By.NAME, By.TAG_NAME, By.CLASS_NAME, By.CSS_SELECTOR
]


class WebDriverTest(BasePytestUnitTestCase):
    def __init__(self, name: str):
        super().__init__(name)
        self.browser_name: NoneStr = None
        self.driver: Optional[WebDriver] = None

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