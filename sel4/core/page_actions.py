import time

from pydantic import validate_arguments
from selenium.common.exceptions import NoSuchWindowException, TimeoutException
from selenium.webdriver.chrome.webdriver import WebDriver

from . import constants
from .shared import check_if_time_limit_exceeded, state_message


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
