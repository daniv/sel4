import time
from datetime import timedelta
from typing import Literal

from loguru import logger
from selenium.webdriver.common.by import By

from .exceptions import TimeLimitExceededException
from .runtime import runtime_store, start_time_ms, time_limit

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


def check_if_time_limit_exceeded():
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
