from typing import TYPE_CHECKING, Optional, Any

from pydantic import validate_arguments, Field
from selenium.webdriver.remote.webelement import WebElement

from sel4.utils.typeutils import OptionalInt

if TYPE_CHECKING:
    from sel4.core.webdriver_test import WebDriverTest


class ShadowElement:
    def __init__(self, proxy: "WebDriverTest"):
        self._proxy = proxy
        self.driver = proxy.driver

    @validate_arguments
    def _get_shadow_element(
            self,
            selector: str = Field(..., strict=True, min_length=1),
            timeout: OptionalInt = None,
            must_be_visible: bool = False,
    ) -> WebElement:
        pass

    @validate_arguments
    def shadow_click(
            self,
            selector: str = Field(..., strict=True, min_length=1),
            timeout: OptionalInt = None,
    ) -> None:
        """

        :param selector:
        :param timeout:
        :return:
        """
        pass

    @validate_arguments
    def wait_for_shadow_element_present(
            self,
            selector: str = Field(..., strict=True, min_length=1),
            timeout: OptionalInt = None
    ) -> WebElement:
        """

        :param selector:
        :param timeout:
        :return:
        """
        pass

    @validate_arguments
    def wait_for_shadow_element_visible(
            self,
            selector: str = Field(..., strict=True, min_length=1),
            timeout: OptionalInt = None,
    ) -> WebElement:
        """

        :param selector:
        :param timeout:
        :return:
        """
        pass

    def is_shadow_element_visible(
            self,
            selector: str = Field(..., strict=True, min_length=1)
    ) -> bool:
        """

        :param selector:
        :return:
        """
        pass

    @validate_arguments
    def wait_for_shadow_element_enabled(
            self,
            selector: str = Field(..., strict=True, min_length=1),
            timeout: OptionalInt = None
    ) -> WebElement:
        """

        :param selector:
        :param timeout:
        :return:
        """
        pass

    def is_shadow_element_enabled(
            self,
            selector: str = Field(..., strict=True, min_length=1)
    ) -> bool:
        """

        :param selector:
        :return:
        """
        pass

    @validate_arguments
    def wait_for_shadow_text_visible(
            self,
            text: str | None,
            selector: str = Field(..., strict=True, min_length=1),
            timeout: OptionalInt = None
    ) -> bool:
        """

        :param text:
        :param selector:
        :param timeout:
        :return:
        """
        pass

    def is_shadow_text_visible(
            self,
            selector: str = Field(..., strict=True, min_length=1)
    ) -> bool:
        """

        :param selector:
        :return:
        """
        pass

    @validate_arguments
    def get_shadow_text(
            self,
            selector: str = Field(..., strict=True, min_length=1),
            timeout: OptionalInt = None
    ) -> Optional[str]:
        """

        :param selector:
        :param timeout:
        :return:
        """
        pass

    @validate_arguments
    def get_shadow_attribute(
            self,
            attribute_name: str,
            selector: str = Field(..., strict=True, min_length=1),
            timeout: OptionalInt = None
    ) -> Optional[Any]:
        """

        :param attribute_name:
        :param selector:
        :param timeout:
        :return:
        """
        pass

    @validate_arguments
    def get_shadow_property(
            self,
            property_name: str,
            selector: str = Field(..., strict=True, min_length=1),
            timeout: OptionalInt = None
    ) -> Optional[Any]:
        """

        :param property_name:
        :param selector:
        :param timeout:
        :return:
        """
        pass

    def is_shadow_attribute_value_present(
            self,
            attribute_name: str = Field(..., strict=True),
            attribute_value: Optional[str | float | int | bool] = None,
            selector: str = Field(..., strict=True, min_length=1)
    ) -> bool:
        """

        :param attribute_name:
        :param attribute_value:
        :param selector:
        :return:
        """
        pass

    @validate_arguments
    def shadow_send_keys(
            self,
            text: str | None,
            selector: str = Field(..., strict=True, min_length=1),
            timeout: OptionalInt = None,
            clear_first: bool = True
    ) -> None:
        """

        :param text:
        :param selector:
        :param timeout:
        :param clear_first:
        :return:
        """
        pass

    def shadow_clear(
            self,
            selector: str = Field(..., strict=True, min_length=1),
            timeout: OptionalInt = None,
    ) -> None:
        """

        :param selector:
        :param timeout:
        :return:
        """
        pass
