import time
from datetime import timedelta
from typing import Literal

from loguru import logger
from selenium.webdriver.common.by import By

from sel4.core.exceptions import TimeLimitExceededException
from sel4.core.runtime import runtime_store, start_time_ms, time_limit

SeleniumBy = Literal[
    By.ID,
    By.XPATH,
    By.LINK_TEXT,
    By.PARTIAL_LINK_TEXT,
    By.NAME,
    By.TAG_NAME,
    By.CLASS_NAME,
    By.CSS_SELECTOR,
]


def state_message(state, now, st, retry, how=None, sel=None, to: float = 0.0):
    import humanize

    def log_message():
        if how and sel:
            state_msg = 'Element {how}="{selector}" {state}\n\twaiting another: {delta}, retry: {retry}'
        else:
            state_msg = "{state}\n\twaiting another: {delta}, retry: {retry}"
        delta = timedelta(milliseconds=st - now)
        precise_delta = humanize.precisedelta(delta, minimum_unit="milliseconds")
        state_msg.format(how=how, selector=sel, state=state, delta=precise_delta, retry=retry)

    logger.opt(lazy=True).debug(lambda: log_message())
    time.sleep(to * 0.2)


def get_exception_message(
        name: Literal[
            "not present", "hidden", "disabled", "stale", "visible", "present", "text", "enabled",
            "attr not present", "attr value", "prop not present", "prop value", "css prop value",
            "css prop not present"
        ],
        how,
        selector,
        timeout,
        **kwargs
) -> str:
    def path(url: str) -> str:
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

    if name == "not present":
        return (
            f'Element {how}="{selector}" on {path}"\n'
            f'\twas not present after {timeout} second{"s" if timeout == 1 else ""}!'
        )
    # if name == "hidden":
    #     return (
    #         f'Element {how}="{selector}" on {path}"\n'
    #         f'\twas hidden after {timeout} second{"s" if timeout == 1 else ""}!'
    #     )
    # if name == "disabled":
    #     return (
    #         f'Element {how}="{selector}" on {path}"\n'
    #         f'\twas disabled after {timeout} second{"s" if timeout == 1 else ""}!'
    #     )
    # if name == "stale":
    #     return (
    #         f'Element {how}="{selector}" on {path}"\n'
    #         f'\twas not present on DOM (stale) after {timeout} second{"s" if timeout == 1 else ""}!'
    #     )
    # if name == "visible":
    #     return (
    #         f'Element {how}="{selector}" on {path}\n'
    #         f'\twas still visible after {timeout} second{"s" if timeout == 1 else ""}!'
    #     )
    # if name == "enabled":
    #     return (
    #         f'Element {how}="{selector}" on {path}\n'
    #         f'\twas still enabled after {timeout} second{"s" if timeout == 1 else ""}!'
    #     )
    # if name == "present":
    #     return (
    #         f'Element {how}="{selector}" on {path}\n'
    #         f'\twas still present after {timeout} second{"s" if timeout == 1 else ""}!'
    #     )
    if name == "text":
        text = kwargs.pop("text")
        return (
            f'Expected text:"{text}" for {how}="{selector}" on {path}\n'
            f'\twas not visible after {timeout} second{"s" if timeout == 1 else ""}!'
        )
    if name == "attr not present":
        attr = kwargs.pop("attr")
        return (
            f'Expected attribute "{attr}" of element {how}="{selector}", on {path}\n'
            f'\twas not present after {timeout} second{"s" if timeout == 1 else ""}!'
        )
    if name == "attr value":
        attr = kwargs.pop("attr")
        val = kwargs.pop("val")
        actual = kwargs.pop("actual")
        return (
            f'Expected value {val} for attribute {attr} of element {how}="{selector}", on {path}\n'
            f'was not present after {timeout} second{"s" if timeout == 1 else ""}! (The actual value was {actual})'
        )
    if name == "prop not present":
        prop = kwargs.pop("prop")
        return (
            f'Expected property "{prop}" of element {how}="{selector}", on {path}\n'
            f'\twas not present after {timeout} second{"s" if timeout == 1 else ""}!'
        )
    if name == "prop value":
        prop = kwargs.pop("prop")
        val = kwargs.pop("val")
        actual = kwargs.pop("actual")
        return (
            f'Expected value {val} for property {prop} of element {how}="{selector}", on {path}\n'
            f'was not present after {timeout} second{"s" if timeout == 1 else ""}! (The actual value was {actual})'
        )
    if name == "css prop not present":
        prop = kwargs.pop("prop")
        return (
            f'Expected css property "{prop}" of element {how}="{selector}", on {path}\n'
            f'\twas not present after {timeout} second{"s" if timeout == 1 else ""}!'
        )
    if name == "css prop value":
        prop = kwargs.pop("prop")
        val = kwargs.pop("val")
        actual = kwargs.pop("actual")
        return (
            f'Expected value {val} for css property {prop} of element {how}="{selector}", on {path}\n'
            f'was not present after {timeout} second{"s" if timeout == 1 else ""}! (The actual value was {actual})'
        )


class SelectorConverter:
    def __init__(self, how: SeleniumBy, selector: str):
        self.how = how
        self.selector = selector

    def convert_to_css_selector(self) -> str:
        """This method converts a selector to a CSS_SELECTOR.
        jQuery commands require a CSS_SELECTOR for finding elements.
        This method should only be used for jQuery/JavaScript actions.
        Pure JavaScript doesn't support using a:contains("LINK_TEXT")."""
        if self.how == By.CSS_SELECTOR or self.how == By.TAG_NAME:
            return self.selector
        elif self.how == By.ID:
            return f"#{self.selector}"
        elif self.how == By.CLASS_NAME:
            return f".{self.selector}"
        elif self.how == By.NAME:
            return f'[name="{self.selector}"]'
        elif self.how == By.XPATH:
            return self.convert_xpath_to_css()
        elif self.how == By.LINK_TEXT:
            return f'a:contains("{self.selector}")'
        elif self.how == By.PARTIAL_LINK_TEXT:
            return f'a:contains("{self.selector}")'
        else:
            raise ValueError(
                f"Exception: Could not convert {self.how}({self.selector}) to CSS_SELECTOR!"
            )

    def convert_xpath_to_css(self):
        from sel4.core.helpers__.translator import convert_xpath_to_css
        return str(convert_xpath_to_css(self.selector))

    def convert_css_to_xpath(self):
        from sel4.core.helpers__.translator import CssTranslator
        return CssTranslator().css_to_xpath(self.selector)


def _are_quotes_escaped(string: str) -> bool:
    if string.count("\\'") != string.count("'") or (
            string.count('\\"') != string.count('"')
    ):
        return True
    return False


def escape_quotes_if_needed(string: str) -> str:
    if _are_quotes_escaped(string):
        if string.count("'") != string.count("\\'"):
            string = string.replace("'", "\\'")
        if string.count('"') != string.count('\\"'):
            string = string.replace('"', '\\"')
    return string


def check_if_time_limit_exceeded():
    from ..runtime import runtime_store, start_time_ms, time_limit
    if runtime_store.get(time_limit, None):
        _time_limit = runtime_store[time_limit]
        now_ms = int(time.time() * 1000)
        _start_time_ms = runtime_store[start_time_ms]
        time_limit_ms = int(_time_limit * 1000.0)

        if now_ms > _start_time_ms + time_limit_ms:
            display_time_limit = time_limit
            plural = "s"
            if float(int(time_limit)) == float(time_limit):
                display_time_limit = int(time_limit)
                if display_time_limit == 1:
                    plural = ""
            message = f"This test has exceeded the time limit of {display_time_limit} second{plural}!"
            message = "\n " + message
            raise TimeLimitExceededException(message)