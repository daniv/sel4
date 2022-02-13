from pydantic import PydanticTypeError, PydanticValueError


class WebDriverInstanceError(PydanticTypeError):
    msg_template = 'WebDriver type expected'


class WebElementInstanceError(PydanticTypeError):
    msg_template = 'WebElement type expected'


class WebElementStaleReferenceError(PydanticValueError):
    code = 'webelement.stale'
    msg_template = 'the element {tag_name}:{locators} is a stale reference'
