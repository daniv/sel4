import time

from loguru import logger
from pydantic import Field, validate_arguments
from selenium.common.exceptions import JavascriptException, WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from sel4.conf import settings
from . import shared
from .runtime import runtime_store, time_limit
from .shared import state_message


@validate_arguments
def wait_for_ready_state_complete(driver: WebDriver, timeout: int = Field(gt=0)):
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
def wait_for_angularjs(driver: WebDriver, timeout: int = Field(gt=0), **kwargs):

    if not settings.WAIT_FOR_ANGULARJS:
        logger.debug("Skipping, settings.WAIT_FOR_ANGULARJS={}", settings.WAIT_FOR_ANGULARJS)
        return
    logger.debug(
        "settings.WAIT_FOR_ANGULARJS={angular}, timeout={} secs", timeout, angular=settings.WAIT_FOR_ANGULARJS
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
        timeout: int = Field(gt=0)
):
    driver.set_script_timeout(timeout)
    return driver.execute_async_script(script)


@validate_arguments
def is_in_frame(driver: WebDriver):
    """
    Returns True if the driver has switched to a frame.
    Returns False if the driver was on default content.
    """
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


@validate_arguments
def get_scroll_distance_to_element(driver: WebDriver, element: WebElement):
    try:
        scroll_position = driver.execute_script("return window.scrollY;")
        element_location = element.location["y"]
        element_location = element_location - 130
        if element_location < 0:
            element_location = 0
        distance = element_location - scroll_position
        return distance
    except WebDriverException:
        return 0


@validate_arguments
def slow_scroll_to_element(element: WebElement):
    scroll_position = element.parent.execute_script("return window.scrollY;")
    element_location = None
    try:
        element_location = element.location["y"]
    except WebDriverException:
        if element_location:
            location = element.location_once_scrolled_into_view
        return
    element_location = element_location - 130
    if element_location < 0:
        element_location = 0
    distance = element_location - scroll_position
    if distance != 0:
        total_steps = int(abs(distance) / 50.0) + 2.0
        step_value = float(distance) / total_steps
        new_position = scroll_position
        for y in range(int(total_steps)):
            time.sleep(0.011)
            new_position += step_value
            scroll_script = "window.scrollTo(0, %s);" % new_position
            element.parent.execute_script(scroll_script)
    time.sleep(0.01)
    scroll_script = "window.scrollTo(0, %s);" % element_location
    element.parent.execute_script(scroll_script)
    time.sleep(0.01)
    if distance > 430 or distance < -300:
        # Add small recovery time for long-distance slow-scrolling
        time.sleep(0.162)
    else:
        time.sleep(0.045)


@validate_arguments
def scroll_to_element(driver: WebDriver, element: WebElement):
    try:
        element_location = element.location["y"]
    except WebDriverException:
        # element.location_once_scrolled_into_view  # Old hack
        return False
    element_location = element_location - 130
    if element_location < 0:
        element_location = 0
    scroll_script = "window.scrollTo(0, %s);" % element_location
    # The old jQuery scroll_script required by=By.CSS_SELECTOR
    # scroll_script = "jQuery('%s')[0].scrollIntoView()" % selector
    try:
        driver.execute_script(scroll_script)
        return True
    except WebDriverException | JavascriptException:
        return False


@validate_arguments
def is_jquery_activated(driver: WebDriver):
    try:
        driver.execute_script("jQuery('html')")  # Fails if jq is not defined
        return True
    except WebDriverException | JavascriptException:
        return False


@validate_arguments
def activate_jquery(driver: WebDriver):
    """
    If "jQuery is not defined", use this method to activate it for use.
    This happens because jQuery is not always defined on web sites.
    """
    try:
        # -- Let's first find out if jQuery is already defined.
        driver.execute_script("jQuery('html');")
        # Since that command worked, jQuery is defined. Let's return.
        return
    except JavascriptException:
        # jQuery is not currently defined. Let's proceed by defining it.
        pass

    jquery_js = dict(settings.RESOURCES_URLS).get("JQUERY")
    add_js_link(driver, jquery_js)
    for x in range(int(settings.MINI_TIMEOUT * 10.0)):
        # jQuery needs a small amount of time to activate.
        try:
            driver.execute_script("jQuery('html');")
            return
        except WebDriverException | JavascriptException:
            time.sleep(0.1)
    try:
        add_js_link(driver, jquery_js)
        time.sleep(0.1)
        driver.execute_script("jQuery('head');")
    except WebDriverException | JavascriptException:
        pass
    # Since jQuery still isn't activating, give up and raise an exception
    raise_unable_to_load_jquery_exception(driver)


@validate_arguments
def add_js_link(driver: WebDriver, js_link: str):

    script_to_add_js = """function injectJS(link) {
          var body_tag=document.getElementsByTagName("body")[0];
          var script_tag=document.createElement("script");
          script_tag.src=link;
          script_tag.type="text/javascript";
          script_tag.crossorigin="anonymous";
          script_tag.defer;
          script_tag.onload=function() { null };
          body_tag.appendChild(script_tag);
       }
       injectJS("%s");"""
    js_link = _escape_quotes_if_needed(js_link)
    driver.execute_script(script_to_add_js % js_link)


@validate_arguments
def raise_unable_to_load_jquery_exception(driver: WebDriver):
    has_csp_error = False
    csp_violation = "violates the following Content Security Policy directive"
    browser_logs = []
    try:
        browser_logs = driver.get_log("browser")
    except (ValueError, WebDriverException):
        pass
    for entry in browser_logs:
        if entry["level"] == "SEVERE":
            if csp_violation in entry["message"]:
                has_csp_error = True
    if has_csp_error:
        raise WebDriverException(
            """Unable to load jQuery on "%s" due to a violation """
            """of the website's Content Security Policy directive. """
            """To override this policy, add "--disable-csp" on the """
            """command-line when running your tests.""" % driver.current_url
        )
    else:
        raise WebDriverException(
            """Unable to load jQuery on "%s" because this website """
            """restricts external JavaScript resources from loading."""
            % driver.current_url
        )


def _are_quotes_escaped(string: str) -> bool:
    if string.count("\\'") != string.count("'") or (
        string.count('\\"') != string.count('"')
    ):
        return True
    return False


def _escape_quotes_if_needed(string: str) -> str:
    if _are_quotes_escaped(string):
        if string.count("'") != string.count("\\'"):
            string = string.replace("'", "\\'")
        if string.count('"') != string.count('\\"'):
            string = string.replace('"', '\\"')
    return string
