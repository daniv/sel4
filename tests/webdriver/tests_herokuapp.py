from typing import TYPE_CHECKING

from selenium.webdriver.common.by import By

if TYPE_CHECKING:
    from sel4.core.webdrivertest import WebDriverTest


def test_add_remove_elements(webdriver_test: "WebDriverTest"):
    # import selenium.webdriver.common.devtools.v96
    # webdriver_test.driver.set_network_conditions(
    #     offline=True,  latency=5,  # additional latency (ms)
    # download_throughput=500 * 1024,  # maximal throughput
    # upload_throughput=500 * 1024)

    webdriver_test.open('http://the-internet.herokuapp.com/')
    webdriver_test.click(By.LINK_TEXT, "Add/Remove Elements")
    webdriver_test.click_link_text("Add/Remove Elements")
