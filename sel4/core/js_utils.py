import time

from loguru import logger
from pydantic import Field, PositiveFloat, validate_arguments
from selenium.common.exceptions import JavascriptException, WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver

from sel4.conf import settings

from ..contrib.pydantic.validators import WebDriverValidator
from . import shared
from .runtime import runtime_store, time_limit
from .shared import state_message


@validate_arguments
def wait_for_ready_state_complete(driver: WebDriver, timeout: PositiveFloat):
    """
    Checks for property "readyState".
    When the value of this becomes "complete", page resources are considered
        fully loaded (although AJAX and other loads might still be happening).
    This method will wait until document.readyState == "complete".
        If the timeout is exceeded, the test will still continue because
        readyState == "interactive" may be good enough.
    """
    t_limit = runtime_store.get(time_limit, 0)
    if runtime_store[time_limit] > 0:
        ...

    logger.debug("Waiting for current page to be readyState='complete'")
    start_ms = time.time() * 1000.0
    stop_ms = start_ms + (timeout * 1000.0)
    for x in range(int(timeout * 10)):
        if t_limit > 0:
            shared.check_if_time_limit_exceeded()
        try:
            ready_state = driver.execute_script("return document.readyState")
        except WebDriverException:
            time.sleep(0.03)
            return True
        if ready_state == "complete":
            time.sleep(0.01)  # -- Better be sure everything is done loading
            return True
        else:
            now_ms = time.time() * 1000.0
            if now_ms >= stop_ms:
                break
            msg = f"readystate is still {ready_state}"
            state_message(state=msg, now=now_ms, st=stop_ms, retry=x + 1, to=timeout)
    return False


@validate_arguments
def wait_for_angularjs(driver: WebDriver, timeout: PositiveFloat, **kwargs):

    if not settings.WAIT_FOR_ANGULARJS:
        logger.debug('Skipping, settings.WAIT_FOR_ANGULARJS={}', settings.WAIT_FOR_ANGULARJS)
        return
    logger.debug(
        'settings.WAIT_FOR_ANGULARJS={angular}, timeout={} secs', timeout, angular=settings.WAIT_FOR_ANGULARJS
    )
    def_pre = "var cb=arguments[arguments.length-1];if(window.angular){"
    prefix = kwargs.pop("prefix", def_pre)
    handler = kwargs.pop("handler", "function(){cb(true)}")
    suffix = kwargs.pop("suffix", "}else{cb(false)}")
    ng_wrapper = (
        f"%(prefix)s"
        "var $elm=document.querySelector("
        "'[data-ng-app],[ng-app],.ng-scope')||document;"
        "if(window.angular && angular.getTestability){"
        "angular.getTestability($elm).whenStable(%(handler)s)"
        "}else{"
        "var $inj;try{$inj=angular.element($elm).injector()||"
        "angular.injector(['ng'])}catch(ex){"
        "$inj=angular.injector(['ng'])};$inj.get=$inj.get||"
        "$inj;$inj.get('$browser')."
        "notifyWhenNoOutstandingRequests(%(handler)s)}"
        "%(suffix)s"
    )
    script = ng_wrapper % {"prefix": prefix, "handler": handler, "suffix": suffix}
    try:
        # This closes any pop-up alerts (otherwise the next part fails)
        driver.execute_script("")
    except (WebDriverException, JavascriptException) as e:
        logger.warning("Exception while execute script -> {}", str(e))
        pass
    try:
        logger.debug("Executing angularjs async script on current webdriver session")
        execute_async_script(driver, script, timeout=timeout)
    except (WebDriverException, JavascriptException):
        time.sleep(0.05)


@validate_arguments
def execute_async_script(
        driver: WebDriver,
        script: str = Field(min_length=5, strict=True),
        timeout: PositiveFloat = None
):
    driver.set_script_timeout(timeout)
    return driver.execute_async_script(script)


def is_in_frame(driver: WebDriver):
    """
    Returns True if the driver has switched to a frame.
    Returns False if the driver was on default content.
    """
    WebDriverValidator.validate(driver)
    in_basic_frame = driver.execute_script(
        """
        var frame = window.frameElement;
        if (frame) {
            return true;
        }
        else {
            return false;
        }
        """
    )
    location_href = driver.execute_script("""return window.location.href;""")
    in_external_frame = False
    if driver.current_url != location_href:
        in_external_frame = True
    if in_basic_frame or in_external_frame:
        return True
    return False
