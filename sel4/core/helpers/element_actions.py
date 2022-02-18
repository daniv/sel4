from typing import List, Optional, Tuple, TYPE_CHECKING

from pydantic import validate_arguments, Field
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from sel4.core import constants
from sel4.core.helpers__.shared import SeleniumBy
from sel4.utils.typeutils import OptionalInt

if TYPE_CHECKING:
    from sel4.core.webdriver_test import WebDriverTest


class ElementActions:
    def __init__(self, proxy: "WebDriverTest"):
        self._proxy = proxy
        self.driver = proxy.driver

    @validate_arguments
    def find_element(
            self,
            how: SeleniumBy,
            selector: str = Field(..., strict=True, min_length=1)
    ) -> WebElement:
        """

        :param how:
        :param selector:
        :return:
        """
        pass

    @validate_arguments
    def find_elements(
            self,
            how: SeleniumBy,
            selector: str = Field(..., strict=True, min_length=1)
    ) -> List[WebElement]:
        """

        :param how:
        :param selector:
        :return:
        """
        pass

    @validate_arguments
    def wait_for_element_present(
            self,
            how: SeleniumBy,
            selector: str = Field(default="", strict=True, min_length=1),
            timeout: OptionalInt = Field(default=constants.MEDIUM_TIMEOUT, gt=0)
    ) -> WebElement:
        """

        :param how:
        :param selector:
        :param timeout:
        :return:
        """
        pass

    @validate_arguments
    def wait_for_element_absent(
            self,
            how: SeleniumBy,
            selector: str = Field(..., strict=True, min_length=1),
            timeout: OptionalInt = Field(default=constants.MEDIUM_TIMEOUT, gt=0)
    ) -> bool:
        """

        :param how:
        :param selector:
        :param timeout:
        :return:
        """
        pass

    @validate_arguments
    def wait_for_element_visible(
            self,
            how: SeleniumBy,
            selector: str = Field(..., strict=True, min_length=1),
            timeout: OptionalInt = Field(default=constants.MEDIUM_TIMEOUT, gt=0)
    ) -> WebElement:
        """

        :param how:
        :param selector:
        :param timeout:
        :return:
        """
        pass

    @validate_arguments
    def wait_for_element_not_visible(
            self,
            how: SeleniumBy,
            selector: str = Field(..., strict=True, min_length=1),
            timeout: OptionalInt = Field(default=constants.MEDIUM_TIMEOUT, gt=0)
    ) -> bool:
        """

        :param how:
        :param selector:
        :param timeout:
        :return:
        """
        pass

    @validate_arguments
    def wait_for_element_enabled(
            self,
            how: SeleniumBy,
            selector: str = Field(default="", strict=True, min_length=1),
            timeout: OptionalInt = Field(default=constants.MEDIUM_TIMEOUT, gt=0)
    ) -> WebElement:
        """

        :param how:
        :param selector:
        :param timeout:
        :return:
        """
        pass

    @validate_arguments
    def wait_for_element_disabled(
            self,
            how: SeleniumBy,
            selector: str = Field(default="", strict=True, min_length=1),
            timeout: OptionalInt = Field(default=constants.MEDIUM_TIMEOUT, gt=0)
    ) -> WebElement:
        """

        :param how:
        :param selector:
        :param timeout:
        :return:
        """
        pass

    @validate_arguments
    def wait_for_link_text_present(
            self,
            link_text: str = Field(..., min_length=1),
            timeout: OptionalInt = Field(default=constants.SMALL_TIMEOUT, gt=0)
    ) -> bool:
        """

        :param link_text:
        :param timeout:
        :return:
        """
        pass

    @validate_arguments
    def wait_for_link_text_visible(
            self,
            link_text: str = Field(..., min_length=1),
            timeout: OptionalInt = Field(default=constants.SMALL_TIMEOUT, gt=0)
    ) -> bool:
        """

        :param link_text:
        :param timeout:
        :return:
        """
        pass

    @validate_arguments
    def wait_for_partial_link_text_present(
            self,
            link_text: str = Field(..., min_length=1),
            timeout: OptionalInt = Field(default=constants.SMALL_TIMEOUT, gt=0)
    ) -> bool:
        """

        :param link_text:
        :param timeout:
        :return:
        """
        pass

    @validate_arguments
    def wait_for_partial_link_text_visible(
            self,
            link_text: str = Field(..., min_length=1),
            timeout: OptionalInt = Field(default=constants.SMALL_TIMEOUT, gt=0)
    ) -> bool:
        """

        :param link_text:
        :param timeout:
        :return:
        """
        pass

    @validate_arguments
    def wait_for_attribute(
            self,
            how: SeleniumBy,
            selector: str = Field(..., strict=True, min_length=1),
            attribute_name: str = Field(..., min_length=1),
            attribute_value: Optional[str | bool | int | float] = Field(..., min_length=1),
            timeout: OptionalInt = Field(default=constants.SMALL_TIMEOUT, gt=0)
    ) -> WebElement:
        """

        :param how:
        :param selector:
        :param attribute_name:
        :param attribute_value:
        :param timeout:
        :return:
        """
        pass

    @validate_arguments
    def wait_for_css_query_selector(
            self,
            css_property_name: str = Field(..., min_length=1),
            css_property_value: Optional[str | bool | int | float] = Field(..., min_length=1),
            selector: str = Field(..., strict=True, min_length=1),
            timeout: OptionalInt = Field(default=constants.SMALL_TIMEOUT, gt=0)
    ) -> WebElement:
        """

        :param css_property_name:
        :param css_property_value:
        :param selector:
        :param timeout:
        :return:
        """
        pass

    @property
    def url_path(self) -> str:
        """
        Return the `httpx.URL.path`` portion of the url
        """
        from httpx import URL
        url = URL(self.driver.current_url)
        return (
            url.path
            if len(url.path) > 1
            else url.host
        )

    @validate_arguments
    def _class_list(
            self,
            webelement: WebElement
    ) -> List[str]:
        """

        :param webelement:
        :return:
        """
        pass

    @validate_arguments
    def _set_element_attributes(
            self,
            webelement: WebElement,
            locators: Tuple[str, str]
    ) -> WebElement:
        """

        :param webelement:
        :param locators:
        :return:
        """
        pass

    def hover_and_click(
            self,
            hover_how: SeleniumBy = Field(default=By.CSS_SELECTOR),
            hover_selector: str = Field(..., strict=True, min_length=1),
            click_how: SeleniumBy = Field(default=By.CSS_SELECTOR),
            click_selector: str = Field(..., strict=True, min_length=1),
            timeout: OptionalInt = Field(default=constants.SMALL_TIMEOUT, gt=0)
    ) -> None:
        """

        :param hover_selector:
        :param click_selector:
        :param hover_how:
        :param click_how:
        :param timeout:
        :return:
        """

    @validate_arguments
    def hover_element(self, element: WebElement):
        """

        :param element:
        :return:
        """

    @validate_arguments
    def hover_element_and_click(
            self,
            element: WebElement,
            click_how: SeleniumBy = Field(default=By.CSS_SELECTOR),
            click_selector: str = Field(..., strict=True, min_length=1),
            timeout: OptionalInt = Field(default=constants.SMALL_TIMEOUT, gt=0)
    ) -> None:
        """

        :param element:
        :param click_how:
        :param click_selector:
        :param timeout:
        :return:
        """
        pass

    @validate_arguments
    def hover_element_and_double_click(
            self,
            element: WebElement,
            click_how: SeleniumBy = Field(default=By.CSS_SELECTOR),
            click_selector: str = Field(..., strict=True, min_length=1),
            timeout: OptionalInt = Field(default=constants.SMALL_TIMEOUT, gt=0)
    ) -> None:
        """

        :param element:
        :param click_how:
        :param click_selector:
        :param timeout:
        :return:
        """
        pass

    def double_click(self, element: WebElement) -> None:
        """

        :param element:
        :return:
        """
        pass