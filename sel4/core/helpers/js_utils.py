import re
import time
from typing import Any

from loguru import logger
from pydantic import Field, validate_arguments
from rich.pretty import Pretty
from selenium.common.exceptions import JavascriptException, WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from ...conf import settings
from ...contrib.pydantic.validators import WebDriverValidator, WebElementValidator
from ...utils.typeutils import NoneStr
from .. import constants
from ..runtime import runtime_store, time_limit, pytestconfig
from .shared import (
    SelectorConverter, SeleniumBy, check_if_time_limit_exceeded,
    escape_quotes_if_needed, state_message,)


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

    logger.trace("Waiting for current page to be readyState='complete'")
    start_ms = time.time() * 1000.0
    stop_ms = start_ms + (timeout * 1000.0)
    for x in range(int(timeout * 10)):
        if t_limit > 0:
            check_if_time_limit_exceeded()
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
    logger.debug("settings.WAIT_FOR_ANGULARJS={angular}, timeout={} secs", timeout, angular=settings.WAIT_FOR_ANGULARJS)
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
def execute_async_script(driver: WebDriver, script: str = Field(min_length=5, strict=True), timeout: int = Field(gt=0)):
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
def get_scroll_distance_to_element(element: WebElement):
    try:
        scroll_position = element.parent.execute_script("return window.scrollY;")
        element_location = element.location["y"]
        element_location = element_location - 130
        if element_location < 0:
            element_location = 0
        distance = element_location - scroll_position
        return distance
    except WebDriverException:
        return 0


def is_jquery_activated(driver: WebDriver):
    driver = WebDriverValidator.validate(driver)
    try:
        driver.execute_script("jQuery('html')")  # Fails if jq is not defined
        return True
    except WebDriverException | JavascriptException:
        return False


def is_html_inspector_activated(driver: WebDriver):
    driver = WebDriverValidator.validate(driver)
    try:
        driver.execute_script("HTMLInspector")  # Fails if not defined
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
    js_link = escape_quotes_if_needed(js_link)
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
            """restricts external JavaScript resources from loading.""" % driver.current_url
        )


@validate_arguments
def js_click(
        driver: WebDriver,
        how: SeleniumBy,
        selector: str = Field(default="", strict=True, min_length=1)
) -> None:
    """Clicks an element using pure JS. Does not use jQuery."""
    css_selector = SelectorConverter(how, selector).convert_to_css_selector()
    css_selector = re.escape(css_selector)  # Add "\\" to special chars
    css_selector = escape_quotes_if_needed(css_selector)
    script = (
        """var simulateClick = function (elem) {
               var evt = new MouseEvent('click', {
                   bubbles: true,
                   cancelable: true,
                   view: window
               });
               var canceled = !elem.dispatchEvent(evt);
           };
           var someLink = document.querySelector('%s');
           simulateClick(someLink);"""
        % css_selector
    )
    driver.execute_script(script)


@validate_arguments
def jquery_slow_scroll_to(
        driver: WebDriver,
        how: SeleniumBy,
        selector: str = Field(default="", strict=True, min_length=1)
) -> None:
    from .element_actions import wait_for_element_present
    element = wait_for_element_present(driver, how, selector, constants.SMALL_TIMEOUT)
    dist = get_scroll_distance_to_element(element)
    time_offset = 0
    try:
        if dist and abs(dist) > settings.SSMD:
            time_offset = int(
                float(abs(dist) - settings.SSMD) / 12.5
            )
            if time_offset > 950:
                time_offset = 950
    except Exception:
        time_offset = 0

    config = runtime_store.get(pytestconfig, None)
    test = getattr(config, "_webdriver_test")
    scroll_time_ms = 550 + time_offset
    sleep_time = 0.625 + (float(time_offset) / 1000.0)
    selector = self.convert_to_css_selector(selector, by=by)
    selector = self.__make_css_match_first_element_only(selector)
    scroll_script = (
        """jQuery([document.documentElement, document.body]).animate({"""
        """scrollTop: jQuery('%s').offset().top - 130}, %s);"""
        % (selector, scroll_time_ms)
    )
    if is_jquery_activated(driver):
        test.execute_script(scroll_script)
    else:
        slow_scroll_to_element(element)
    test.sleep(sleep_time)


@validate_arguments
def jquery_click(
    driver: WebDriver, how: SeleniumBy, selector: str = Field(default="", strict=True, min_length=1)
) -> None:
    """Clicks an element using jQuery. Different from using pure JS."""
    from .element_actions import wait_for_element_interactable

    wait_for_element_interactable(how, selector, timeout=constants.SMALL_TIMEOUT)
    selector = self.convert_to_css_selector(selector, by=by)
    selector = self.__make_css_match_first_element_only(selector)
    click_script = """jQuery('%s')[0].click();""" % selector
    safe_execute_script(driver, click_script)


def safe_execute_script(driver: WebDriver, script, *args) -> Any:
    """
    When executing a script that contains a jQuery command,
    it's important that the jQuery library has been loaded first.
    This method will load jQuery if it wasn't already loaded.
    """
    WebDriverValidator.validate(driver)
    if not is_jquery_activated(driver):
        activate_jquery()
    return driver.execute_script(script, *args)


def slow_scroll_to_element(element: WebElement) -> None:
    element = WebElementValidator.validate(element)
    try:
        _slow_scroll_to_element(element)
    except WebDriverException | JavascriptException:
        # Scroll to the element instantly if the slow scroll fails
        scroll_to_element(element)


def scroll_to_element(element: WebElement) -> bool:
    element = WebElementValidator.validate(element)
    try:
        element_location = element.location["y"]
    except WebDriverException:
        return False
    element_location = element_location - 130
    if element_location < 0:
        element_location = 0
    scroll_script = "window.scrollTo(0, %s);" % element_location
    try:
        element.parent.execute_script(scroll_script)
        return True
    except WebDriverException | JavascriptException:
        return False


def _slow_scroll_to_element(element: WebElement):
    element = WebElementValidator.validate(element)
    scroll_position = element.parent.execute_script("return window.scrollY;")
    try:
        element_location = element.location["y"]
    except WebDriverException:
        location = element.location_once_scrolled_into_view()
        pretty = Pretty(location, justify="left")
        logger.debug("location_once_scrolled_into_view -> {}", pretty)
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
        logger.trace("Add small recovery time for long-distance slow-scrolling")
        time.sleep(0.162)
    else:
        time.sleep(0.045)


def highlight_with_js(driver: WebDriver, selector: str = Field(..., strict=True, min_length=1), o_bs: NoneStr = None):
    try:
        logger.debug("Closes any pop-up alerts")
        driver.execute_script("")
    except JavascriptException:
        pass
    script = (
        """document.querySelector('%s').style.boxShadow =
        '0px 0px 6px 6px rgba(128, 128, 128, 0.5)';"""
        % selector
    )
    try:
        driver.execute_script(script)
    except WebDriverException | JavascriptException:
        return
    for n in range(settings.HIGHLIGHT_LOOPS):
        script = (
            """document.querySelector('%s').style.boxShadow =
            '0px 0px 6px 6px rgba(255, 0, 0, 1)';"""
            % selector
        )
        driver.execute_script(script)
        time.sleep(0.0181)
        script = (
            """document.querySelector('%s').style.boxShadow =
            '0px 0px 6px 6px rgba(128, 0, 128, 1)';"""
            % selector
        )
        driver.execute_script(script)
        time.sleep(0.0181)
        script = (
            """document.querySelector('%s').style.boxShadow =
            '0px 0px 6px 6px rgba(0, 0, 255, 1)';"""
            % selector
        )
        driver.execute_script(script)
        time.sleep(0.0181)
        script = (
            """document.querySelector('%s').style.boxShadow =
            '0px 0px 6px 6px rgba(0, 255, 0, 1)';"""
            % selector
        )
        driver.execute_script(script)
        time.sleep(0.0181)
        script = (
            """document.querySelector('%s').style.boxShadow =
            '0px 0px 6px 6px rgba(128, 128, 0, 1)';"""
            % selector
        )
        driver.execute_script(script)
        time.sleep(0.0181)
        script = (
            """document.querySelector('%s').style.boxShadow =
            '0px 0px 6px 6px rgba(128, 0, 128, 1)';"""
            % selector
        )
        driver.execute_script(script)
        time.sleep(0.0181)
    script = """document.querySelector('%s').style.boxShadow =
        '%s';""" % (
        selector,
        o_bs,
    )
    driver.execute_script(script)


def highlight_with_jquery(
    driver: WebDriver, selector: str = Field(..., strict=True, min_length=1), o_bs: NoneStr = None
):
    try:
        # This closes any pop-up alerts
        driver.execute_script("")
    except WebDriverException | JavascriptException:
        pass
    script = (
        """jQuery('%s').css('box-shadow',
        '0px 0px 6px 6px rgba(128, 128, 128, 0.5)');"""
        % selector
    )
    safe_execute_script(driver, script)
    for n in range(settings.HIGHLIGHT_LOOPS):
        script = (
            """jQuery('%s').css('box-shadow',
            '0px 0px 6px 6px rgba(255, 0, 0, 1)');"""
            % selector
        )
        driver.execute_script(script)
        time.sleep(0.0181)
        script = (
            """jQuery('%s').css('box-shadow',
            '0px 0px 6px 6px rgba(128, 0, 128, 1)');"""
            % selector
        )
        driver.execute_script(script)
        time.sleep(0.0181)
        script = (
            """jQuery('%s').css('box-shadow',
            '0px 0px 6px 6px rgba(0, 0, 255, 1)');"""
            % selector
        )
        driver.execute_script(script)
        time.sleep(0.0181)
        script = (
            """jQuery('%s').css('box-shadow',
            '0px 0px 6px 6px rgba(0, 255, 0, 1)');"""
            % selector
        )
        driver.execute_script(script)
        time.sleep(0.0181)
        script = (
            """jQuery('%s').css('box-shadow',
            '0px 0px 6px 6px rgba(128, 128, 0, 1)');"""
            % selector
        )
        driver.execute_script(script)
        time.sleep(0.0181)
        script = (
            """jQuery('%s').css('box-shadow',
            '0px 0px 6px 6px rgba(128, 0, 128, 1)');"""
            % selector
        )
        driver.execute_script(script)
        time.sleep(0.0181)
    script = """jQuery('%s').css('box-shadow', '%s');""" % (selector, o_bs)
    driver.execute_script(script)


def add_css_link(driver, css_link):
    script_to_add_css = """function injectCSS(css) {
          var head_tag=document.getElementsByTagName("head")[0];
          var link_tag=document.createElement("link");
          link_tag.rel="stylesheet";
          link_tag.type="text/css";
          link_tag.href=css;
          link_tag.crossorigin="anonymous";
          head_tag.appendChild(link_tag);
       }
       injectCSS("%s");"""
    css_link = escape_quotes_if_needed(css_link)
    driver.execute_script(script_to_add_css % css_link)


def add_js_link(driver, js_link):
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
    js_link = escape_quotes_if_needed(js_link)
    driver.execute_script(script_to_add_js % js_link)


def add_css_style(driver, css_style):
    add_css_style_script = """function injectStyle(css) {
          var head_tag=document.getElementsByTagName("head")[0];
          var style_tag=document.createElement("style");
          style_tag.type="text/css";
          style_tag.appendChild(document.createTextNode(css));
          head_tag.appendChild(style_tag);
       }
       injectStyle("%s");"""
    css_style = css_style.replace("\n", "")
    css_style = escape_quotes_if_needed(css_style)
    driver.execute_script(add_css_style_script % css_style)


def add_js_code_from_link(driver: WebDriver, js_link: str):
    driver = WebDriverValidator.validate(driver)
    if js_link.startswith("//"):
        js_link = "http:" + js_link
    import httpx

    js_code = httpx.get(js_link).text
    add_js_code_script = (
        """var body_tag=document.getElementsByTagName('body').item(0);"""
        """var script_tag=document.createElement("script");"""
        """script_tag.type="text/javascript";"""
        """script_tag.onload=function() { null };"""
        """script_tag.appendChild(document.createTextNode("%s"));"""
        """body_tag.appendChild(script_tag);"""
    )
    js_code = js_code.replace("\n", " ")
    js_code = escape_quotes_if_needed(js_code)
    driver.execute_script(add_js_code_script % js_code)


def add_js_code(driver: WebDriver, js_code: str):
    driver = WebDriverValidator.validate(driver)
    add_js_code_script = (
        """var body_tag=document.getElementsByTagName('body').item(0);"""
        """var script_tag=document.createElement("script");"""
        """script_tag.type="text/javascript";"""
        """script_tag.onload=function() { null };"""
        """script_tag.appendChild(document.createTextNode("%s"));"""
        """body_tag.appendChild(script_tag);"""
    )
    js_code = js_code.replace("\n", " ")
    js_code = escape_quotes_if_needed(js_code)
    driver.execute_script(add_js_code_script % js_code)


def add_meta_tag(driver: WebDriver, http_equiv=None, content=None):
    driver = WebDriverValidator.validate(driver)
    if http_equiv is None:
        http_equiv = "Content-Security-Policy"
    if content is None:
        content = "default-src *; style-src 'self' 'unsafe-inline'; " \
                  "script-src: 'self' 'unsafe-inline' 'unsafe-eval'"
    script_to_add_meta = """function injectMeta() {
           var meta_tag=document.createElement('meta');
           meta_tag.httpEquiv="%s";
           meta_tag.content="%s";
           document.getElementsByTagName('head')[0].appendChild(meta_tag);
        }
        injectMeta();""" % (
        http_equiv,
        content,
    )
    driver.execute_script(script_to_add_meta)
