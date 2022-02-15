from typing import Tuple, List

from pydantic import validate_arguments, Field
from selenium.common.exceptions import (
    WebDriverException,
    JavascriptException
)
from selenium.webdriver.remote.webelement import WebElement


@validate_arguments
def has_attribute(
        webelement: WebElement,
        attr_name: str = Field(strict=True, min_length=2)
) -> bool:
    try:
        has = webelement.parent.execute_script(f"return arguments[0].hasAttribute({attr_name});")
        return has
    except WebDriverException | JavascriptException:
        return False


def set_element_attributes(
        webelement: WebElement,
        locators: Tuple[str, str]
) -> WebElement:
    """
    Set element additional attributes for debugging purposes
    Will skipped if `settings.DEBUG` is False

    :param webelement: The :class:`WebElement` instance
    :param locators: a tuples of the locators (how, value)
    """

    if not settings.DEBUG:
        return webelement

    def repr_decorator():
        yield "id", webelement.id
        yield "tag", webelement.tag_name
        yield "displayed", webelement.is_displayed()
        yield "enabled", webelement.is_enabled()
        yield "classes", class_list
        if hasattr(webelement, "locators"):
            yield "locators", getattr(webelement, "locators")

    setattr(webelement, "locators", [locators])
    setattr(webelement, "__rich_repr__", repr_decorator)
    setattr(webelement, "class_list", class_list(webelement))
    return webelement


@validate_arguments
def class_list(
        webelement: WebElement
) -> List[str]:
    """
    Returns a stripped list of the ``webelement.get_dom_attribute('class')``
    """
    if webelement.get_attribute("class") is not None:
        klass = webelement.get_attribute("class").strip().split()
        return remove_empty_string(klass)
    return []