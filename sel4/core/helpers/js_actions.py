from typing import TYPE_CHECKING, Optional, Any

from pydantic import validate_arguments, Field
from selenium.webdriver.remote.webelement import WebElement

from sel4.core import constants
from sel4.core.helpers__.shared import SeleniumBy
from sel4.utils.typeutils import OptionalInt, NoneStr

if TYPE_CHECKING:
    from sel4.core.webdriver_test import WebDriverTest


class JavascriptActions:
    def __init__(self, proxy: "WebDriverTest"):
        self._proxy = proxy
        self.driver = proxy.driver

    @validate_arguments
    def wait_for_ready_state_complete(
            self, timeout: OptionalInt = Field(default=constants.MEDIUM_TIMEOUT, gt=0)
    ) -> None:
        """

        :param timeout:
        :return:
        """

    @validate_arguments
    def wait_for_angularjs(
            self, timeout: OptionalInt = Field(default=constants.MEDIUM_TIMEOUT, gt=0)
    ) -> None:
        """

        :param timeout:
        :return:
        """

    @validate_arguments
    def execute_async_script(
            self, script: str = Field(min_length=5, strict=True),
            timeout: OptionalInt = Field(default=constants.MEDIUM_TIMEOUT, gt=0)
    ) -> Optional[Any]:
        """

        :param script:
        :param timeout:
        :return:
        """
        pass

    @validate_arguments
    def execute_script(
            self, script: str = Field(min_length=5, strict=True),
            timeout: OptionalInt = Field(default=constants.MEDIUM_TIMEOUT, gt=0)
    ) -> Optional[Any]:
        """

        :param script:
        :param timeout:
        :return:
        """
        pass

    @validate_arguments
    def safe_execute_script(
            self, script: str = Field(min_length=5, strict=True),
            timeout: OptionalInt = Field(default=constants.MEDIUM_TIMEOUT, gt=0)
    ) -> Optional[Any]:
        """

        :param script:
        :param timeout:
        :return:
        """
        pass

    def is_in_frame(self) -> bool:
        """

        :return:
        """
        pass

    @validate_arguments
    def get_scroll_distance_to_element(self, element: WebElement) -> int:
        """

        :param element:
        :return:
        """

    def is_jquery_activated(self) -> bool:
        """

        :return:
        """

    def activate_jquery(self) -> bool:
        """

        :return:
        """
        pass

    def raise_unable_to_load_jquery_exception(self) -> None:
        """

        :return:
        """
        pass

    @validate_arguments
    def jquery_slow_scroll_to(
            self,
            how: SeleniumBy,
            selector: str = Field(..., strict=True, min_length=1)
    ) -> None:
        """

        :param how:
        :param selector:
        :return:
        """
        pass

    @validate_arguments
    def jquery_click(
            self,
            how: SeleniumBy,
            selector: str = Field(..., strict=True, min_length=1)
    ) -> None:
        """

        :param how:
        :param selector:
        :return:
        """
        pass

    def is_html_inspector_activated(self) -> bool:
        """

        :return:
        """
        pass

    @validate_arguments
    def add_js_link(self, js_link: str) -> None:
        """

        :param js_link:
        :return:
        """
        pass

    @validate_arguments
    def add_css_link(self, css_link: str) -> None:
        """

        :param css_link:
        :return:
        """
        pass

    @validate_arguments
    def add_css_style(self, css_style: str) -> None:
        """

        :param css_style:
        :return:
        """
        pass

    @validate_arguments
    def add_js_code_from_link(self, js_link: str) -> None:
        """

        :param js_link:
        :return:
        """
        pass

    @validate_arguments
    def add_js_code(self, js_code: str) -> None:
        """

        :param js_code:
        :return:
        """
        pass

    @validate_arguments
    def add_meta_tag(self, http_equiv: NoneStr = None, content: NoneStr = None) -> None:
        """

        :param http_equiv:
        :param content:
        :return:
        """
        pass

    @validate_arguments
    def js_click(
            self,
            how: SeleniumBy,
            selector: str = Field(..., strict=True, min_length=1)
    ) -> None:
        """

        :param how:
        :param selector:
        :return:
        """
        pass

    def _slow_scroll_to_element(self, element: WebElement) -> bool:
        ...

    def slow_scroll_to_element(self, element: WebElement) -> bool:
        """

        :param element:
        :return:
        """
        pass

    def scroll_to_element(self, element: WebElement) -> bool:
        """

        :param element:
        :return:
        """
        pass

    def highlight_with_js(
            self,
            selector: str = Field(..., strict=True, min_length=1),
            o_bs: NoneStr = None
    ) -> None:
        """

        :param selector:
        :param o_bs:
        :return:
        """
        pass

    def highlight_with_jquery(
            self,
            selector: str = Field(..., strict=True, min_length=1),
            o_bs: NoneStr = None
    ) -> None:
        """

        :param selector:
        :param o_bs:
        :return:
        """
        pass

