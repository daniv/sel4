import pathlib
import time
from typing import List, Optional

from pydantic import validate_arguments, Field
from selenium.common.exceptions import (
    NoSuchWindowException,
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
    ElementNotInteractableException,
    ElementNotVisibleException,
    StaleElementReferenceException
)
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from sel4.conf import settings
from . import constants
from .shared import (
    check_if_time_limit_exceeded,
    state_message,
    get_exception_message,
    SeleniumBy
)
from .element_actions import (
    set_element_attributes,
    has_attribute
)
from ..utils.strutils import get_uuid4
from ..utils.typeutils import OptionalInt, NoneStr


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
            check_if_time_limit_exceeded()
            try:
                window_handle = driver.window_handles[window]
                driver.switch_to.window(window_handle)
                return True
            except IndexError as e:
                now_ms = time.time() * 1000.0
                if now_ms >= stop_ms:
                    exception = e
                    break
                state_message(f"Switching to window {window}", now_ms, stop_ms, x + 1, to=timeout)

        message = f'Window {window} was not present after {timeout} second{"s" if timeout == 1 else ""}!'
        if not exception:
            exception = Exception
        raise TimeoutException(msg=f"\n {exception.__class__.__qualname__}: {message}")

    else:
        window_handle = window
        for x in range(int(timeout * 10)):
            check_if_time_limit_exceeded()
            try:
                driver.switch_to.window(window_handle)
                return True
            except NoSuchWindowException as e:
                now_ms = time.time() * 1000.0
                if now_ms >= stop_ms:
                    exception = e
                    break
                state_message(f"Switching to window {window}", now_ms, stop_ms, x + 1, to=timeout)

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


@validate_arguments
def find_element(
        driver: WebDriver,
        how: SeleniumBy,
        selector: str = Field(default="", strict=True, min_length=1)
) -> WebElement:
    """
    Finds and element, wrapping :meth:`WebDriver.find_element`

    :param driver: the current web driver
    :param how: the type of selector being used (required)
    :param selector: the locator for identifying the page element (required)
    :return: an instance of WebElement
    :raises: NoSuchElementException, if the element was not found
    """
    # -- validating arguments
    try:
        webelement = driver.find_element(by=how, value=selector)
        return set_element_attributes(webelement, (how, selector))
    except NoSuchElementException:
        message = str(get_exception_message("not present", how, selector, 0.0))
        raise TimeoutException(msg=f"\n {NoSuchElementException.__class__.__qualname__}: {message}")


@validate_arguments
def find_elements(
        driver: WebDriver,
        how: SeleniumBy,
        selector: str = Field(default="", strict=True, min_length=1)
) -> List[WebElement]:
    """
    Finds a group of elements, wrapping :meth:`WebDriver.find_elements`

    :param driver: the current web driver
    :param how: the type of selector being used (required)
    :param selector: the locator for identifying the page element (required)
    :return: a list of WebElements or empty list if nothing was found
    """
    webelements = driver.find_elements(by=how, value=selector)
    if len(webelements):
        return list(map(lambda x: set_element_attributes(x, (how, selector)), webelements))
    return []


@validate_arguments
def wait_for_element_present(
        driver: WebDriver,
        how: SeleniumBy,
        selector: str = Field(default="", strict=True, min_length=1),
        timeout: OptionalInt = constants.LARGE_TIMEOUT
) -> WebElement:
    """
    Searches for the specified element by the given selector. Returns the
    element object if it exists in the HTML. (The element can be invisible.)

    :param driver: the current web driver
    :param how: the type of selector being used
    :param selector: the locator for identifying the page element
    :param timeout: the time to wait for the element in seconds
    :returns: The element object if it exists in the HTML. (The element can be invisible.)
    :raises TimeoutException: if the element does not exist in the HTML within the specified timeout.
    """
    start_ms = time.time() * 1_000.0
    stop_ms = start_ms + (timeout * 1_000.0)

    for x in range(int(timeout * 10)):
        check_if_time_limit_exceeded()
        try:
            webelement = driver.find_element(by=how, value=selector)
            return set_element_attributes(webelement, (how, selector))
        except NoSuchElementException:
            now_ms = time.time() * 1_000.0
            if now_ms >= stop_ms:
                break
            state_message("is not present", now_ms, stop_ms, x + 1, how, selector, timeout)

    message = get_exception_message("not present", how, selector, timeout)
    raise TimeoutException(msg=f"\n {NoSuchElementException.__class__.__qualname__}: {message}")


@validate_arguments
def wait_for_element_absent(
        driver: WebDriver,
        how: SeleniumBy,
        selector: str = Field(default="", strict=True, min_length=1),
        timeout: OptionalInt = constants.LARGE_TIMEOUT
) -> bool:
    """
    Searches for the specified element by the given selector.
    Raises an exception if the element is still present after the specified timeout.

    :param driver: the current web driver
    :param how: the type of selector being used
    :param selector: the locator for identifying the page element
    :param timeout: the time to wait for the element in seconds
    :raises TimeoutException: if the element still exist in the HTML within the specified timeout.
    """
    start_ms = time.time() * 1000.0
    stop_ms = start_ms + (timeout * 1000.0)

    for x in range(int(timeout * 10)):
        check_if_time_limit_exceeded()
        try:
            driver.find_element(by=how, value=selector)
            now_ms = time.time() * 1000.0
            if now_ms >= stop_ms:
                break
            state_message("is still present", now_ms, stop_ms, x + 1, how, selector, timeout)
        except NoSuchElementException:
            return True

    message = str(get_exception_message("present", how, selector, timeout))
    raise TimeoutException(msg=f"\n {WebDriverException.__class__.__qualname__}: {message}")


@validate_arguments
def wait_for_element_visible(
        driver: WebDriver,
        how: SeleniumBy,
        selector: str = Field(default="", strict=True, min_length=1),
        timeout: OptionalInt = constants.LARGE_TIMEOUT
) -> WebElement:
    """
    Searches for the specified element by the given selector. Returns the
    element object if the element is present and visible on the page.

    :param driver: the current web driver
    :param how: the type of selector being used.
    :param selector: the locator for identifying the page element.
    :param timeout: the time to wait for the element in seconds
    :returns: A WebElement object if the element is displayed
    :raises TimeoutException:
    if the element exists in the HTML, but is not visible within the specified timeout.
    """
    is_present = False
    is_stale = False
    start_ms = time.time() * 1000.0
    stop_ms = start_ms + (timeout * 1000.0)

    for x in range(int(timeout * 10)):
        check_if_time_limit_exceeded()
        try:
            webelement = driver.find_element(by=how, value=selector)
            is_present = True
            if webelement.is_displayed():
                return set_element_attributes(webelement, (how, selector))
            else:
                raise ElementNotVisibleException()
        except NoSuchElementException:
            now_ms = time.time() * 1000.0
            if now_ms >= stop_ms:
                break
            state_message("is not present", now_ms, stop_ms, x + 1, how, selector, timeout)
        except StaleElementReferenceException:
            is_stale = True
            now_ms = time.time() * 1000.0
            if now_ms >= stop_ms:
                break
            state_message("is no longer on DOM", now_ms, stop_ms, x + 1, how, selector, timeout)
        except ElementNotVisibleException:
            now_ms = time.time() * 1000.0
            if now_ms >= stop_ms:
                break
            state_message("is not visible", now_ms, stop_ms, x + 1, how, selector, timeout)

    if not is_present:
        message = get_exception_message("not present", how, selector, timeout)
        raise TimeoutException(msg=f"\n {NoSuchElementException.__class__.__qualname__}: {message}")
    if is_stale:
        message = get_exception_message("stale", how, selector, timeout)
        raise TimeoutException(msg=f"\n {StaleElementReferenceException.__class__.__qualname__}: {message}")

    message = get_exception_message("hidden", how, selector, timeout)
    raise TimeoutException(msg=f"\n {ElementNotVisibleException.__class__.__qualname__}: {message}")


def wait_for_element_not_visible(
        driver: WebDriver,
        how: SeleniumBy,
        selector: str = Field(default="", strict=True, min_length=1),
        timeout: OptionalInt = constants.LARGE_TIMEOUT
):
    """
    Searches for the specified element by the given selector.
    Raises an exception if the element is still visible after the specified timeout.

    :param driver: the current web driver
    :param how: the type of selector being used.
    :param selector: the locator for identifying the page element.
    :param timeout: the time to wait for the element in seconds
    :returns: A WebElement object if the element is displayed
    :raises TimeoutException: if the element is still visible after the specified timeout.
    """
    start_ms = time.time() * 1000.0
    stop_ms = start_ms + (timeout * 1000.0)
    for x in range(int(timeout * 10)):
        check_if_time_limit_exceeded()
        try:
            element = driver.find_element(by=how, value=selector)
            if element.is_displayed():
                now_ms = time.time() * 1000.0
                if now_ms >= stop_ms:
                    break
                state_message("still visible", now_ms, stop_ms, x + 1, how, selector, timeout)
            else:
                return True
        except NoSuchElementException | StaleElementReferenceException:
            return True

    message = get_exception_message("visible", how, selector, timeout)
    raise TimeoutException(msg=f"\n {WebDriverException.__class__.__qualname__}: {message}")


@validate_arguments
def wait_for_element_interactable(
        driver: WebDriver,
        how: SeleniumBy,
        selector: str = Field(default="", strict=True, min_length=1),
        timeout: OptionalInt = constants.LARGE_TIMEOUT
) -> WebElement:
    """
    Searches for the specified element by the given selector.
    Raises an exception if the element is disabled or css disabled after the specified timeout.

    :param driver: the current web driver
    :param how: the type of selector being used
    :param selector: the locator for identifying the page element (required)
    :param timeout: the time to wait for the element in seconds
    :raises TimeoutException:
    if the element does not exist in the HTML or
    if the element was removed from the DOM during interaction
    if the element exist but is not displayed on page or
    if the element exists in the HTML, visible, but disabled within the specified timeout.
    """
    is_present = False
    is_stale = False
    is_displayed = False
    start_ms = time.time() * 1000.0
    stop_ms = start_ms + (timeout * 1000.0)

    for x in range(int(timeout * 10)):
        check_if_time_limit_exceeded()
        try:
            webelement: WebElement = driver.find_element(by=how, value=selector)
            is_present = True
            if webelement.is_displayed():
                is_displayed = True
            else:
                raise ElementNotVisibleException()
            if has_attribute(webelement, "disabled"):
                raise ElementNotInteractableException()
            if webelement.is_enabled():
                return set_element_attributes(webelement, (how, selector))
            raise ElementNotInteractableException()

        except NoSuchElementException:
            now_ms = time.time() * 1000.0
            if now_ms >= stop_ms:
                break
            state_message("is not present", now_ms, stop_ms, x + 1, how, selector, timeout)
        except StaleElementReferenceException:
            is_stale = True
            now_ms = time.time() * 1000.0
            if now_ms >= stop_ms:
                break
            state_message("is no longer on DOM", now_ms, stop_ms, x + 1, how, selector, timeout)
        except ElementNotVisibleException:
            now_ms = time.time() * 1000.0
            if now_ms >= stop_ms:
                break
            state_message("is not visible", now_ms, stop_ms, x + 1, how, selector, timeout)
        except ElementNotInteractableException:
            now_ms = time.time() * 1000.0
            if now_ms >= stop_ms:
                break
            state_message("is disabled", now_ms, stop_ms, x + 1, how, selector, timeout)

    if not is_present:
        message = get_exception_message("not present", how, selector, timeout)
        raise TimeoutException(msg=f"\n {NoSuchElementException.__class__.__qualname__}: {message}")
    if is_stale:
        message = get_exception_message("stale", how, selector, timeout)
        raise TimeoutException(msg=f"\n {StaleElementReferenceException.__class__.__qualname__}: {message}")
    if not is_displayed:
        message = get_exception_message("hidden", how, selector, timeout)
        raise TimeoutException(msg=f"\n {StaleElementReferenceException.__class__.__qualname__}: {message}")

    message = get_exception_message("disabled", how, selector, timeout)
    raise TimeoutException(msg=f"\n {ElementNotInteractableException.__class__.__qualname__}: {message}")


@validate_arguments
def wait_for_element_disabled(
        driver: WebDriver,
        how: SeleniumBy,
        selector: str = Field(default="", strict=True, min_length=1),
        timeout: OptionalInt = constants.LARGE_TIMEOUT
) -> WebElement:
    """
    Searches for the specified element by the given selector.
    Raises an exception if the element is enabled after the specified timeout.

    :param driver: the current web driver
    :param how: the type of selector being used
    :param selector: the locator for identifying the page element (required)
    :param timeout: the time to wait for the element in seconds
    :raises TimeoutException:
    if the element does not exist in the HTML or
    if the element was removed from the DOM during interaction
    if the element exist but is not displayed on page or
    if the element exists in the HTML, visible, but enabled within the specified timeout.
    """
    is_present = False
    is_stale = False
    is_displayed = False
    start_ms = time.time() * 1000.0
    stop_ms = start_ms + (timeout * 1000.0)

    for x in range(int(timeout * 10)):
        check_if_time_limit_exceeded()
        try:
            webelement: WebElement = driver.find_element(by=how, value=selector)
            is_present = True
            if webelement.is_displayed():
                is_displayed = True
            else:
                raise ElementNotVisibleException()
            if has_attribute(webelement, "disabled"):
                return set_element_attributes(webelement, (how, selector))
            if webelement.is_enabled():
                raise ValueError()
            return set_element_attributes(webelement, (how, selector))

        except NoSuchElementException:
            now_ms = time.time() * 1000.0
            if now_ms >= stop_ms:
                break
            state_message("is not present", now_ms, stop_ms, x + 1, how, selector, timeout)
        except StaleElementReferenceException:
            is_stale = True
            now_ms = time.time() * 1000.0
            if now_ms >= stop_ms:
                break
            state_message("is no longer on DOM", now_ms, stop_ms, x + 1, how, selector, timeout)
        except ElementNotVisibleException:
            now_ms = time.time() * 1000.0
            if now_ms >= stop_ms:
                break
            state_message("is not visible", now_ms, stop_ms, x + 1, how, selector, timeout)
        except ValueError:
            now_ms = time.time() * 1000.0
            if now_ms >= stop_ms:
                break
            state_message("is still enabled", now_ms, stop_ms, x + 1, how, selector, timeout)

    if not is_present:
        message = get_exception_message("not present", how, selector, timeout)
        raise TimeoutException(msg=f"\n {NoSuchElementException.__class__.__qualname__}: {message}")
    if is_stale:
        message = get_exception_message("stale", how, selector, timeout)
        raise TimeoutException(msg=f"\n {StaleElementReferenceException.__class__.__qualname__}: {message}")
    if not is_displayed:
        message = get_exception_message("hidden", how, selector, timeout)
        raise TimeoutException(msg=f"\n {ElementNotVisibleException.__class__.__qualname__}: {message}")

    message = get_exception_message("enabled", how, selector, timeout)
    raise TimeoutException(msg=f"\n {WebDriverException.__class__.__qualname__}: {message}")

