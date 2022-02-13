from typing_extensions import Literal

from sel4.utils.envutils import env
from sel4.utils.typeutils import OptionalInt, OptionalBool, LogLevelName

PROJECT_ROOT = None

PROJECT_PATHS = []

ROOT_LOG_LEVEL: LogLevelName = "WARNING"

# Inbucket Email address that error messages come from.
SERVER_EMAIL_EXTENSION = None

MIN_ANY_STR_LENGTH = 0
MAX_ANY_STR_LENGTH: OptionalInt = None

# If True, switch to new tabs/windows automatically if a click opens a new one.
# (This switch only happens if the initial tab is still on same URL as before,
# which prevents a situation where a click opens up a new URL in the same tab,
# where a pop-up might open up a new tab on its own, leading to a double open.
# If False, the browser will stay on the current tab where the click happened.
SWITCH_TO_NEW_TABS_ON_CLICK: OptionalBool = None

# Default browser resolutions when opening new windows for tests.
# (Headless resolutions take priority, and include all browsers.)
# (Firefox starts maximized by default when running in GUI Mode.)
CHROME_START_WIDTH = 1250
CHROME_START_HEIGHT = 840
HEADLESS_START_WIDTH = 1440
HEADLESS_START_HEIGHT = 1880
# Disabling the Content Security Policy of the browser by default.
DISABLE_CSP_ON_FIREFOX: OptionalBool = None
DISABLE_CSP_ON_CHROME: OptionalBool = None
# If True and --proxy=IP_ADDRESS:PORT is invalid, then error immediately.
RAISE_INVALID_PROXY_STRING_EXCEPTION: OptionalBool = None

# This adds wait_for_ready_state_complete() after various browser actions.
# Setting this to True may improve reliability at the cost of speed.
# Called after self.open(url) or self.open_url(url), NOT self.driver.open(url)
WAIT_FOR_RSC_ON_PAGE_LOADS: OptionalBool = None
# Called after self.click(selector), NOT element.click()
WAIT_FOR_RSC_ON_CLICKS: OptionalBool = None
# This adds wait_for_angularjs() after various browser actions.
# (Requires WAIT_FOR_RSC_ON_PAGE_LOADS and WAIT_FOR_RSC_ON_CLICKS to also be on.)
WAIT_FOR_ANGULARJS: OptionalBool = None

# Default time to wait after each browser action performed during Demo Mode.
# Use Demo Mode when you want others to see what your automation is doing.
# Usage: "--demo_mode". (Can be overwritten by using "--demo_sleep=TIME".)
DEFAULT_DEMO_MODE_TIMEOUT: OptionalInt = None

# -- A list of supported browsers ,should be overridden in the sel4.settings.${env}.py
WEBDRIVER_MANAGER_ROOT = None
WEB_DRIVER_MANAGER_VERSION_MODE = "compatible"
WEB_DRIVER_MANAGER_SHOW_PROGRESS = True
WEBDRIVER_SETTINGS = {}
WEBDRIVER_MANAGER_PATHS = []
