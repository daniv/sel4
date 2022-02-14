from typing import TYPE_CHECKING, Any, Dict

from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from . import _errors as errors

__all__ = ["WebDriverValidator", "WebElementValidator", "register_validators"]


if TYPE_CHECKING:
    from ...utils.typeutils import CallableGenerator


def webdriver_validator(v: Any) -> WebDriver:
    if isinstance(v, WebDriver):
        return v
    raise errors.WebDriverInstanceError


def webelement_validator(v: Any) -> WebElement:
    if isinstance(v, WebElement):
        return v
    raise errors.WebElementInstanceError


def webelement_stale_validator(v: WebElement) -> WebElement:
    try:
        v.is_displayed()
        return v
    except StaleElementReferenceException:
        locators = getattr(v, "locators")
        raise errors.WebElementStaleReferenceError(
            tag_name=v.tag_name, locators=locators
        )


def register_validators():
    from pydantic import validators as pydantic_validators

    validators = getattr(pydantic_validators, "_VALIDATORS")
    validators.append((WebDriver, [webdriver_validator]))
    validators.append((WebElement, [webelement_validator, webelement_stale_validator]))


class WebDriverValidator(WebDriver):
    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        field_schema.update(type="webdriver")

    @classmethod
    def __get_validators__(cls) -> "CallableGenerator":
        yield webdriver_validator

    @classmethod
    def validate(cls, value: Any) -> WebDriver:
        return webdriver_validator(value)


class WebElementValidator(WebElement):
    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        field_schema.update(type="webdriver")

    @classmethod
    def __get_validators__(cls) -> "CallableGenerator":
        yield cls.validate

    @classmethod
    def validate(cls, value: Any) -> WebElement:
        return webelement_validator(value)
