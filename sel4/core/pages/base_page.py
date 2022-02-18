from functools import cached_property
from typing import TYPE_CHECKING

from httpx import URL

if TYPE_CHECKING:
    from sel4.core.webdrivertest import WebDriverTest


class Page:
    def __init__(self, base_test_case: "WebDriverTest"):
        self.test = base_test_case

    @cached_property
    def url(self) -> URL:
        """
        Return the ``driver.current_url`` to an `httpx.URL``
        """
        return URL(self.test.driver.current_url)

    @cached_property
    def url_path(self) -> str:
        """
        Return the `httpx.URL.path`` portion of the url
        """
        return (
            self.url.path
            if len(self.url.path) > 1
            else self.url.host
        )

    @cached_property
    def alias(self):
        from functools import reduce
        return reduce(
            lambda x, y: x + ('_' if y.isupper() else '') + y, self.__class__.__qualname__
        ).lower()
