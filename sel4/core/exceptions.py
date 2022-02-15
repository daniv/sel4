import sys
from typing import Optional, Sequence

from selenium.common.exceptions import WebDriverException
from ..utils.strutils import host_tag, thread_tag, platform_label


class ImproperlyConfigured(Exception):
    """
    Framework is somehow improperly configured
    """

    pass


class OutOfScopeException(Exception):
    """
    Used by BaseCase methods when setUp() is skipped
    """


class TimeLimitExceededException(Exception):
    pass


class BaseExtendedWebDriverException(WebDriverException):
    def __init__(
            self,
            msg: Optional[str] = None,
            screen: Optional[str] = None,
            stacktrace: Optional[Sequence[str]] = None
    ) -> None:
        if not stacktrace:
            from rich.traceback import Traceback
            exc_type, exc_value, traceback = sys.exc_info()
            stacktrace = Traceback.extract(exc_type, exc_value, traceback, show_locals=False)
        super(BaseExtendedWebDriverException, self).__init__(msg, screen, stacktrace)
        self.thread = thread_tag()
        self.host = host_tag()
        self.platform = platform_label()


class ExtendedTimeoutException:
    pass

