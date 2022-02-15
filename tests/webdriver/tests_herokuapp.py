from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sel4.core.webdrivertest import WebDriverTest


def test_add_remove_elements(webdriver_test: "WebDriverTest"):
    webdriver_test.open('http://the-internet.herokuapp.com/')
    webdriver_test.click("Add/Remove Elements")
