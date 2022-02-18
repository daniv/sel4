import re
import time
from typing import Tuple, List, TYPE_CHECKING

from pydantic import validate_arguments, Field
from selenium.common.exceptions import (
    WebDriverException,
    JavascriptException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementNotVisibleException,
    TimeoutException,
    ElementNotInteractableException
)
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from .shared import (
    SeleniumBy,
    check_if_time_limit_exceeded,
    state_message,
    get_exception_message
)
from .. import constants
from .shared import escape_quotes_if_needed
from ..runtime import runtime_store, pytestconfig
from ...conf import settings
from ...contrib.pydantic.validators import WebElementValidator
from ...utils.typeutils import OptionalInt, NoneStr

if TYPE_CHECKING:
    from pytest import Config


# region Find Functions

@validate_arguments
def find_element(
        driver: WebDriver,
        how: SeleniumBy,
        selector: str = Field(..., strict=True, min_length=1)
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
        selector: str = Field(..., strict=True, min_length=1)
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

# endregion Find Functions


# region Wait Functions

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

    message = (
        f'Element {how}="{selector}" on {url_path(driver.current_url)}"\n'
        f'\twas not present after {timeout} second{"s" if timeout == 1 else ""}!'
    )
    raise TimeoutException(msg=f"\n {NoSuchElementException.__class__.__qualname__}: {message}")


@validate_arguments
def wait_for_element_absent(
        driver: WebDriver,
        how: SeleniumBy,
        selector: str = Field(..., strict=True, min_length=1),
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

    message = (
        f'Element {how}="{selector}" on {url_path(driver.current_url)}\n'
        f'\twas still present after {timeout} second{"s" if timeout == 1 else ""}!'
    )
    raise TimeoutException(msg=f"\n {WebDriverException.__class__.__qualname__}: {message}")


@validate_arguments
def wait_for_element_visible(
        driver: WebDriver,
        how: SeleniumBy,
        selector: str = Field(..., strict=True, min_length=1),
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
        message = (
            f'Element {how}="{selector}" on {url_path(driver.current_url)}\n'
            f'\twas still present after {timeout} second{"s" if timeout == 1 else ""}!'
        )
        raise TimeoutException(msg=f"\n {NoSuchElementException.__class__.__qualname__}: {message}")

    path = url_path(driver.current_url)
    if is_stale:
        message = (
            f'Element {how}="{selector}" on {path}"\n'
            f'\twas not present on DOM (stale) after {timeout} second{"s" if timeout == 1 else ""}!'
        )
        raise TimeoutException(msg=f"\n {StaleElementReferenceException.__class__.__qualname__}: {message}")

    message = (
        f'Element {how}="{selector}" on {path}"\n'
        f'\twas hidden after {timeout} second{"s" if timeout == 1 else ""}!'
    )
    raise TimeoutException(msg=f"\n {ElementNotVisibleException.__class__.__qualname__}: {message}")


@validate_arguments
def wait_for_element_not_visible(
        driver: WebDriver,
        how: SeleniumBy,
        selector: str = Field(..., strict=True, min_length=1),
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

    message = (
        f'Element {how}="{selector}" on {url_path(driver.current_url)}\n'
        f'\twas still visible after {timeout} second{"s" if timeout == 1 else ""}!'
    )
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

    path = url_path(driver.current_url)
    if not is_present:
        message = (
            f'Element {how}="{selector}" on {path}"\n'
            f'\twas not present after {timeout} second{"s" if timeout == 1 else ""}!'
        )
        raise TimeoutException(msg=f"\n {NoSuchElementException.__class__.__qualname__}: {message}")
    if is_stale:
        message = (
            f'Element {how}="{selector}" on {path}"\n'
            f'\twas not present on DOM (stale) after {timeout} second{"s" if timeout == 1 else ""}!'
        )
        raise TimeoutException(msg=f"\n {StaleElementReferenceException.__class__.__qualname__}: {message}")
    if not is_displayed:
        message = (
            f'Element {how}="{selector}" on {path}"\n'
            f'\twas hidden after {timeout} second{"s" if timeout == 1 else ""}!'
        )
        raise TimeoutException(msg=f"\n {StaleElementReferenceException.__class__.__qualname__}: {message}")

    message = (
        f'Element {how}="{selector}" on {path}"\n'
        f'\twas disabled after {timeout} second{"s" if timeout == 1 else ""}!'
    )
    raise TimeoutException(msg=f"\n {ElementNotInteractableException.__class__.__qualname__}: {message}")


@validate_arguments
def wait_for_element_disabled(
        driver: WebDriver,
        how: SeleniumBy,
        selector: str = Field(..., strict=True, min_length=1),
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

    path = url_path(driver.current_url)
    if not is_present:
        message = (
            f'Element {how}="{selector}" on {path}"\n'
            f'\twas not present after {timeout} second{"s" if timeout == 1 else ""}!'
        )
        raise TimeoutException(msg=f"\n {NoSuchElementException.__class__.__qualname__}: {message}")
    if is_stale:
        message = (
            f'Element {how}="{selector}" on {path}"\n'
            f'\twas not present on DOM (stale) after {timeout} second{"s" if timeout == 1 else ""}!'
        )
        raise TimeoutException(msg=f"\n {StaleElementReferenceException.__class__.__qualname__}: {message}")
    if not is_displayed:
        message = (
            f'Element {how}="{selector}" on {path}"\n'
            f'\twas hidden after {timeout} second{"s" if timeout == 1 else ""}!'
        )
        raise TimeoutException(msg=f"\n {ElementNotVisibleException.__class__.__qualname__}: {message}")

    message = (
        f'Element {how}="{selector}" on {path}\n'
        f'\twas still enabled after {timeout} second{"s" if timeout == 1 else ""}!'
    )
    raise TimeoutException(msg=f"\n {WebDriverException.__class__.__qualname__}: {message}")


@validate_arguments
def wait_for_link_text_present(
        driver: WebDriver,
        link_text: str = Field(...),
        timeout: OptionalInt = constants.SMALL_TIMEOUT
):
    config: "Config" = runtime_store[pytestconfig]
    test = getattr(config, "_webdriver_test")
    start_ms = time.time() * 1000.0
    stop_ms = start_ms + (timeout * 1000.0)

    for x in range(int(timeout * 10)):
        check_if_time_limit_exceeded()
        try:
            if not test.is_link_text_present(link_text):
                raise ValueError()
            return
        except ValueError:
            now_ms = time.time() * 1000.0
            if now_ms >= stop_ms:
                break
            state_message(f'Link text "{link_text}" was not found!', now_ms, stop_ms, x + 1, to=timeout)

        path = url_path(driver.current_url)
        message = (
            f'Link text "{link_text}" on {path}"\n'
            f'\twas not present after {timeout} second{"s" if timeout == 1 else ""}!'
        )
        raise TimeoutException(msg=f"\n {NoSuchElementException.__class__.__qualname__}: {message}")


@validate_arguments
def wait_for_partial_link_text_present(
        driver: WebDriver,
        link_text: str = Field(...),
        timeout: OptionalInt = constants.SMALL_TIMEOUT
):
    config: "Config" = runtime_store[pytestconfig]
    test = getattr(config, "_webdriver_test")
    start_ms = time.time() * 1000.0
    stop_ms = start_ms + (timeout * 1000.0)

    for x in range(int(timeout * 10)):
        check_if_time_limit_exceeded()
        try:
            if not test.is_partial_link_text_present(link_text):
                raise ValueError()
            return
        except ValueError:
            now_ms = time.time() * 1000.0
            if now_ms >= stop_ms:
                break
            state_message(f'Partial link text "{link_text}" was not found!', now_ms, stop_ms, x + 1, to=timeout)

        path = url_path(driver.current_url)
        message = (
            f'Partial link text "{link_text}" on {path}"\n'
            f'\twas not present after {timeout} second{"s" if timeout == 1 else ""}!'
        )
        raise TimeoutException(msg=f"\n {NoSuchElementException.__class__.__qualname__}: {message}")


@validate_arguments
def wait_for_css_query_selector(
        driver: WebDriver,
        selector: str = Field(..., strict=True, min_length=1),
        timeout: OptionalInt = constants.SMALL_TIMEOUT
) -> WebElement:
    start_ms = time.time() * 1000.0
    stop_ms = start_ms + (timeout * 1000.0)
    for x in range(int(timeout * 10)):
        try:
            selector = re.escape(selector)
            selector = escape_quotes_if_needed(selector)
            element = driver.execute_script(
                """return document.querySelector('%s')""" % selector
            )
            if element:
                return element
        except WebDriverException | JavascriptException:
            element = None
        if not element:
            now_ms = time.time() * 1000.0
            if now_ms >= stop_ms:
                break
            state_message("is not present", now_ms, stop_ms, x + 1, "jquery", selector, timeout)

    message = (
        f'Element jquery="{selector}" on {url_path(driver.current_url)}"\n'
        f'\twas not present after {timeout} second{"s" if timeout == 1 else ""}!'
    )
    raise TimeoutException(msg=f"\n {NoSuchElementException.__class__.__qualname__}: {message}")

# endregion Wait Functions


def double_click(element: WebElement):
    demo_mode_highlight_if_active(element)
    if not self.demo_mode and not self.slow_mode:
        self.__scroll_to_element(element, selector, by)
    self.wait_for_ready_state_complete()
    # Find the element one more time in case scrolling hid it
    element = page_actions.wait_for_element_visible(
        self.driver, selector, by, timeout=timeout
    )
    pre_action_url = self.driver.current_url


@validate_arguments
def has_attribute(
        webelement: WebElement,
        attr_name: str = Field(strict=True, min_length=2)
) -> bool:
    try:
        has = webelement.parent.execute_script(f"return arguments[0].hasAttribute({attr_name});")
        return has
    except WebDriverException | JavascriptException:
        return False

# region Service Functions


def url_path(url: str) -> str:
    """
    Return the `httpx.URL.path`` portion of the url
    """
    from httpx import URL
    url = URL(url)
    return (
        url.path
        if len(url.path) > 1
        else url.host
    )


def set_element_attributes(
        webelement: WebElement,
        locators: Tuple[str, str]
) -> WebElement:
    """
    Set element additional attributes for debugging purposes
    Will skipped if `settings.DEBUG` is False

    :param webelement: The :class:`WebElement` instance
    :param locators: a tuples of the locators (how, value)
    """

    if not settings.DEBUG:
        return webelement

    def repr_decorator():
        yield "id", webelement.id
        yield "tag", webelement.tag_name
        yield "displayed", webelement.is_displayed()
        yield "enabled", webelement.is_enabled()
        yield "classes", class_list
        if hasattr(webelement, "locators"):
            yield "locators", getattr(webelement, "locators")

    setattr(webelement, "locators", [locators])
    setattr(webelement, "__rich_repr__", repr_decorator)
    setattr(webelement, "class_list", class_list(webelement))
    return webelement


@validate_arguments
def class_list(
        webelement: WebElement
) -> List[str]:
    """
    Returns a stripped list of the ``webelement.get_dom_attribute('class')``
    """
    if webelement.get_attribute("class") is not None:
        klass = webelement.get_attribute("class").strip().split()
        from sel4.utils.iterutils import remove_empty_string
        return remove_empty_string(klass)
    return []

# endregion Service Functions


# region Highlight Functions





# endregion Highlight Functions


def hover_element(element: WebElement):
    """
    Similar to hover_on_element(), but uses found element, not a selector.
    """
    hover = ActionChains(driver).move_to_element(element)
    hover.perform()


def hover_on_element(driver, selector, by=By.CSS_SELECTOR):
    """
    Fires the hover event for the specified element by the given selector.
    @Params
    driver - the webdriver object (required)
    selector - the locator for identifying the page element (required)
    by - the type of selector being used (Default: By.CSS_SELECTOR)
    """
    element = driver.find_element(by=by, value=selector)
    hover = ActionChains(driver).move_to_element(element)
    hover.perform()


def hover_and_click(
        driver,
        hover_selector,
        click_selector,
        hover_by=By.CSS_SELECTOR,
        click_by=By.CSS_SELECTOR,
        timeout=settings.SMALL_TIMEOUT,
):
    """
    Fires the hover event for a specified element by a given selector, then
    clicks on another element specified. Useful for dropdown hover based menus.
    @Params
    driver - the webdriver object (required)
    hover_selector - the css selector to hover over (required)
    click_selector - the css selector to click on (required)
    hover_by - the hover selector type to search by (Default: By.CSS_SELECTOR)
    click_by - the click selector type to search by (Default: By.CSS_SELECTOR)
    timeout - number of seconds to wait for click element to appear after hover
    """
    start_ms = time.time() * 1000.0
    stop_ms = start_ms + (timeout * 1000.0)
    element = driver.find_element(by=hover_by, value=hover_selector)
    hover = ActionChains(driver).move_to_element(element)
    for x in range(int(timeout * 10)):
        try:
            hover.perform()
            element = driver.find_element(by=click_by, value=click_selector)
            element.click()
            return element
        except Exception:
            now_ms = time.time() * 1000.0
            if now_ms >= stop_ms:
                break
            time.sleep(0.1)
    plural = "s"
    if timeout == 1:
        plural = ""
    message = "Element {%s} was not present after %s second%s!" % (
        click_selector,
        timeout,
        plural,
    )
    timeout_exception(NoSuchElementException, message)


def hover_element_and_click(
        driver,
        element,
        click_selector,
        click_by=By.CSS_SELECTOR,
        timeout=settings.SMALL_TIMEOUT,
):
    """
    Similar to hover_and_click(), but assumes top element is already found.
    """
    start_ms = time.time() * 1000.0
    stop_ms = start_ms + (timeout * 1000.0)
    hover = ActionChains(driver).move_to_element(element)
    for x in range(int(timeout * 10)):
        try:
            hover.perform()
            element = driver.find_element(by=click_by, value=click_selector)
            element.click()
            return element
        except Exception:
            now_ms = time.time() * 1000.0
            if now_ms >= stop_ms:
                break
            time.sleep(0.1)
    plural = "s"
    if timeout == 1:
        plural = ""
    message = "Element {%s} was not present after %s second%s!" % (
        click_selector,
        timeout,
        plural,
    )
    timeout_exception(NoSuchElementException, message)


def hover_element_and_double_click(
        driver,
        element,
        click_selector,
        click_by=By.CSS_SELECTOR,
        timeout=settings.SMALL_TIMEOUT,
):
    start_ms = time.time() * 1000.0
    stop_ms = start_ms + (timeout * 1000.0)
    hover = ActionChains(driver).move_to_element(element)
    for x in range(int(timeout * 10)):
        try:
            hover.perform()
            element_2 = driver.find_element(by=click_by, value=click_selector)
            actions = ActionChains(driver)
            actions.move_to_element(element_2)
            actions.double_click(element_2)
            actions.perform()
            return element_2
        except Exception:
            now_ms = time.time() * 1000.0
            if now_ms >= stop_ms:
                break
            time.sleep(0.1)
    plural = "s"
    if timeout == 1:
        plural = ""
    message = "Element {%s} was not present after %s second%s!" % (
        click_selector,
        timeout,
        plural,
    )
    timeout_exception(NoSuchElementException, message)