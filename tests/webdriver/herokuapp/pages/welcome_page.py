from typing import Tuple

from sel4.core.helpers.shared import SeleniumBy
from sel4.core.pages.base_page import Page
from sel4.core.webdrivertest import WebDriverTest


class WelcomePage(Page):
    _SELECTORS = []

    def __init__(self, base_test_case: "WebDriverTest"):
        super().__init__(base_test_case)

    @classmethod
    def get_selector(cls, name: str) -> Tuple[SeleniumBy, str]: