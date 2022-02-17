import time

from _pytest import unittest
from loguru import logger
from pydantic import Field, validate_arguments, PositiveInt
from rich.highlighter import ReprHighlighter

from sel4.utils.typeutils import OptionalFloat, OptionalInt

from .runtime import runtime_store
from ..conf import settings


class BasePytestUnitTestCase(unittest.UnitTestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._highlighter = ReprHighlighter()
        self._called_setup = False
        self._called_teardown = False
        self._is_timeout_changed = False
        self._time_limit: OptionalFloat = None
        self._start_time_ms: OptionalInt = None

        self.__deferred_assert_count = 0
        self.__deferred_assert_failures = []
        self.__visual_baseline_copies = []

    def __get_new_timeout(self, timeout: OptionalInt = None) -> int:
        import math

        try:
            timeout_multiplier = float(self.config.getoption("timeout_multiplier", 1))
            if timeout_multiplier <= 0.5:
                timeout_multiplier = 0.5
            timeout = int(math.ceil(timeout_multiplier * timeout))
            return timeout
        except ArithmeticError | Exception:
            # Wrong data type for timeout_multiplier (expecting int or float)
            return timeout

    @validate_arguments
    def set_time_limit(self, time_limit: OptionalFloat = None):
        if time_limit:
            from .runtime import time_limit

            runtime_store[time_limit] = time_limit
        else:
            runtime_store[time_limit] = None
        current_time_limit = runtime_store[time_limit]
        if current_time_limit and current_time_limit > 0:
            self._time_limit = runtime_store[time_limit]
        else:
            self._time_limit = None
            runtime_store[time_limit] = None

    @validate_arguments
    def get_timeout(
            self,
            timeout: OptionalInt = None,
            default_tm: int = Field(strict=True, gt=0)
    ) -> int:
        if not timeout:
            return default_tm
        if self.config.getoption("timeout_multiplier", None) and timeout == default_tm:
            logger.debug("Recalculating new timeout")
            return self.__get_new_timeout(timeout)
        return timeout

    @staticmethod
    def get_beautiful_soup(source: str):
        """
        BeautifulSoup is a toolkit for dissecting an HTML document
        and extracting what you need. It's great for screen-scraping!
        See: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
        """
        from bs4 import BeautifulSoup
        logger.debug("Create instance of BeautifulSoup base on page source")
        soup = BeautifulSoup(source, "html.parser")
        return soup

    def _slow_mode_pause_if_active(self):
        if self.config.getoption("slow_mode", False):
            wait_time = settings.DEFAULT_DEMO_MODE_TIMEOUT
            if self.config.getoption("demo_sleep", False):
                wait_time = float(self.config.getoption("demo_sleep"))
            time.sleep(wait_time)
