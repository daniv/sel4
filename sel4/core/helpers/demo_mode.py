import time
from typing import TYPE_CHECKING

from loguru import logger
from pydantic import Field, validate_arguments
from selenium.common.exceptions import (
    StaleElementReferenceException, ElementNotInteractableException
)
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from .shared import SeleniumBy
from ..runtime import pytestconfig, runtime_store
from ...conf import settings
from ...utils.typeutils import OptionalInt
from .js_utils import (
    get_scroll_distance_to_element
)
from .. import constants

if TYPE_CHECKING:
    from pytest import Config


def demo_mode_scroll_if_active(
        how: SeleniumBy,
        selector: str = Field(default="", strict=True, min_length=1)
) -> None:
    config: "Config" = runtime_store[pytestconfig]
    demo_mode = config.getoption("demo_mode", skip=True)
    if demo_mode:
        logger.debug('Demo node: slow scrolling to {}:"{}"', how.upper(), selector)
        test = getattr(config, "_webdriver_test")
        test.slow_scroll_to(how, selector)


def demo_mode_pause_if_active(tiny=False):
    config: "Config" = runtime_store[pytestconfig]
    demo_mode = config.getoption("demo_mode", skip=True)
    if demo_mode:
        logger.debug("Pausing demo mode ...")
        wait_time = settings.DEFAULT_DEMO_MODE_TIMEOUT
        if config.getoption("demo_sleep", False):
            wait_time = float(config.getoption("demo_sleep"))
        if not tiny:
            time.sleep(wait_time)
        else:
            time.sleep(wait_time / 3.4)
    elif config.getoption("slow_mode", None):
        logger.debug("Pausing slow mode ...")
        test = getattr(config, "_webdriver_test")
        getattr(test, "_slow_mode_pause_if_active")()


@validate_arguments
def demo_mode_highlight_if_active(
        driver: WebDriver,
        how: SeleniumBy,
        selector: str = Field(default="", strict=True, min_length=1),
) -> None:
    config: "Config" = runtime_store[pytestconfig]
    demo_mode = config.getoption("demo_mode", skip=True)
    slow_mode = config.getoption("slow_mode", False)
    test = getattr(config, "_webdriver_test")

    if demo_mode:
        # Includes self.slow_scroll_to(selector, by=by) by default
        test.highlight(how, selector)
    elif slow_mode:
        # Just do the slow scroll part of the highlight() method
        time.sleep(0.08)
        from .element_actions import wait_for_element_visible
        element = wait_for_element_visible(how, selector, timeout=constants.SMALL_TIMEOUT)
        try:
            scroll_distance = get_scroll_distance_to_element(driver, element)
            if abs(scroll_distance) > settings.SSMD:
                self.__jquery_slow_scroll_to(selector, by)
            else:
                self.__slow_scroll_to_element(element)
        except StaleElementReferenceException | ElementNotInteractableException:
            test.wait_for_ready_state_complete()
            time.sleep(0.12)
            element = self.wait_for_element_visible(
                selector, by=by, timeout=settings.SMALL_TIMEOUT
            )
            self.__slow_scroll_to_element(element)
        time.sleep(0.12)


def _slow_scroll_to_element(element: WebElement):
    try:
        slow_scroll_to_element(self.driver, element, self.browser)
    except Exception:
        # Scroll to the element instantly if the slow scroll fails
        scroll_to_element(element)