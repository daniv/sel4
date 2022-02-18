import pathlib
import time
from typing import Optional

from pydantic import validate_arguments, Field
from selenium.common.exceptions import (
    NoSuchWindowException,
    TimeoutException,
    NoSuchElementException,
    WebDriverException
)
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.webdriver import WebDriver

from ...conf import settings
from ...core import constants
from ...core.helpers__.shared import SeleniumBy
from ...core.helpers__ import shared
from ...utils.strutils import get_uuid4
from ...utils.typeutils import NoneStr


def _get_last_page(driver: WebDriver):
    try:
        last_page = driver.current_url
    except WebDriverException:
        last_page = "[WARNING! Browser Not Open!]"
    if len(last_page) < 5:
        last_page = "[WARNING! Browser Not Open!]"
    return last_page


@validate_arguments
def switch_to_window(driver: WebDriver, window: int | str, timeout: int = constants.SMALL_TIMEOUT):
    """
    Wait for a window to appear, and switch to it. This should be usable
    as a drop-in replacement for driver.switch_to.window().

    :param driver: the webdriver object
    :param window: the window index or window handle
    :param timeout: the time to wait for the window in seconds
    """
    start_ms = time.time() * 1000.0
    stop_ms = start_ms + (timeout * 1000.0)
    exception = None
    if isinstance(window, int):
        for x in range(int(timeout * 10)):
            shared.check_if_time_limit_exceeded()
            try:
                window_handle = driver.window_handles[window]
                driver.switch_to.window(window_handle)
                return True
            except IndexError as e:
                now_ms = time.time() * 1000.0
                if now_ms >= stop_ms:
                    exception = e
                    break
                shared.state_message(f"Switching to window {window}", now_ms, stop_ms, x + 1, to=timeout)

        message = f'Window {window} was not present after {timeout} second{"s" if timeout == 1 else ""}!'
        if not exception:
            exception = Exception
        raise TimeoutException(msg=f"\n {exception.__class__.__qualname__}: {message}")

    else:
        window_handle = window
        for x in range(int(timeout * 10)):
            shared.check_if_time_limit_exceeded()
            try:
                driver.switch_to.window(window_handle)
                return True
            except NoSuchWindowException as e:
                now_ms = time.time() * 1000.0
                if now_ms >= stop_ms:
                    exception = e
                    break
                shared.state_message(f"Switching to window {window}", now_ms, stop_ms, x + 1, to=timeout)

        message = f'Window {window} was not present after{timeout} second{"s" if timeout == 1 else ""}!'
        if not exception:
            exception = Exception
        raise TimeoutException(msg=f"\n {exception.__class__.__qualname__}: {message}")


def save_screenshot(
        driver: WebDriver,
        how: Optional[SeleniumBy],
        selector: NoneStr = Field(default=None, strict=True, min_length=1)
) -> pathlib.Path:
    """
    Saves a screenshot of the current page.
    If no folder is specified, uses the folder where pytest was called.
    The screenshot will include the entire page unless a selector is given.
    If a provided selector is not found, then takes a full-page screenshot.
    The screenshot will be in PNG format: (*.png)
    """
    screenshot_path: pathlib.Path = dict(settings.PROJECT_PATHS).get("SCREENSHOTS")
    file_name = f'{get_uuid4()}.png'
    screenshot_path = screenshot_path.joinpath(file_name)
    if selector:
        try:
            element = driver.find_element(by=how, value=selector)
            element_png = element.screenshot_as_png
            with open(screenshot_path, "wb") as file:
                file.write(element_png)
        except WebDriverException:
            if driver:
                driver.get_screenshot_as_file(screenshot_path)
            else:
                pass
    else:
        if driver:
            driver.get_screenshot_as_file(screenshot_path)
        else:
            pass

    return screenshot_path


@validate_arguments
def is_element_visible(
        driver: WebDriver,
        how: SeleniumBy,
        selector: str = Field(default="", strict=True, min_length=1)
) -> bool:
    """
    Returns whether the specified element selector is visible on the page.

    :param driver: The Webdriver instance
    :param how: the By locator
    :param selector: the selector value
    :return: True if element is visible, otherwise False
    """
    try:
        element = driver.find_element(by=how, value=selector)
        return element.is_displayed()
    except NoSuchElementException:
        return False


@validate_arguments
def is_element_enabled(
        driver: WebDriver,
        how: SeleniumBy,
        selector: str = Field(default="", strict=True, min_length=1)
) -> bool:
    """
    Returns whether the specified element selector is enabled on the page

    :param driver: The Webdriver instance
    :param how: the By locator
    :param selector: the selector value
    :return: True if element is visible, otherwise False
    """
    try:
        element = driver.find_element(by=how, value=selector)
        return element.is_enabled()
    except NoSuchElementException:
        return False


@validate_arguments
def is_element_present(
        driver: WebDriver,
        how: SeleniumBy,
        selector: str = Field(default="", strict=True, min_length=1)
) -> bool:
    """
    Returns whether the specified element selector is present on the page.

    :param driver: The Webdriver instance
    :param how: the By locator
    :param selector: the selector value
    :return: True if element is present, otherwise False
    """
    try:
        driver.find_element(by=how, value=selector)
        return True
    except NoSuchElementException:
        return False


