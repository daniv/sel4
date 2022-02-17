from typing import ParamSpec, ParamSpecArgs

from loguru import logger
from pydantic import validate_arguments, Field, constr
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver

from ...contrib.pydantic.validators import WebDriverValidator


def clear_out_console_logs(driver: WebDriver):
    driver = WebDriverValidator.validate(driver)
    try:
        # Clear out the current page log before navigating to a new page
        # (To make sure that assert_no_js_errors() uses current results)
        logger.debug("Cleaning web-driver console logs before navigating to a new page...")
        for log_type in driver.log_types:
            driver.get_log(log_type)
    except WebDriverException:
        pass


@validate_arguments
def open_url(
        driver: WebDriver,
        url: str = Field(strict=True, min_length=4),
        tries: int = Field(default=2, ge=1)
):
    clear_out_console_logs(driver)
    func = driver.get
    from ...utils.retries import retry_call
    retry_call(func, f_args=[url], tries=tries, backoff=2.0, delay=0.5, exceptions=WebDriverException)
