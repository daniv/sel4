import os
import pathlib

from typing_extensions import Literal

from sel4 import env
from sel4.core import constants

DEBUG = False

# this variable will be set during bootstrap
PROJECT_ROOT = pathlib.Path(os.environ["PROJECT_ROOT"])

# Absolute filesystem path to the directory that will hold resources
RESOURCES_ROOT = PROJECT_ROOT.joinpath("resources")

# Folder that stores the logs, screenshots, reports and all the information on run-time.
EXECUTION_ROOT = PROJECT_ROOT.joinpath("out")

PROJECT_PATHS = [("LAST_EXECUTION", EXECUTION_ROOT.joinpath("pytest_exec"))]

CACHE_NAME = "sel4"

JQUERY_VERSION = "3.6.0"

RESOURCES_URLS = [
    ("JQUERY", f"https://cdnjs.cloudflare.com/ajax/libs/jquery/{JQUERY_VERSION}/jquery.min.js")
]

WEBDRIVER_MANAGER_PATHS = [
    ("downloads", PROJECT_ROOT.joinpath("webdrivers/downloads")),
    ("executables", PROJECT_ROOT.joinpath("webdrivers/bin")),
]

SUPPORTED_BROWSERS = Literal[
    constants.Browser.GOOGLE_CHROME,
    constants.Browser.FIREFOX,
    constants.Browser.SAFARI,
    constants.Browser.EDGE,
    constants.Browser.REMOTE,
]

# Reports widths
HTML_WIDTH = "1675px"
HIGHLIGHT_LOOPS = 2
# Demo Mode has slow scrolling to see where you are on the page better.
# However, a regular slow scroll takes too long to cover big distances.
# If the scroll distance is greater than SSMD, a slow scroll speeds up.
# Smooth Scroll Minimum Distance (for advanced slow scroll)
SSMD = 900

SWITCH_TO_NEW_TABS_ON_CLICK = env("SWITCH_TO_NEW_TABS_ON_CLICK", bool, True)

# Default browser resolutions when opening new windows for tests.
# (Headless resolutions take priority, and include all browsers.)
# (Firefox starts maximized by default when running in GUI Mode.)
CHROME_START_WIDTH = 1250
CHROME_START_HEIGHT = 840
HEADLESS_START_WIDTH = 1440
HEADLESS_START_HEIGHT = 1880

# Disabling the Content Security Policy of the browser by default.
DISABLE_CSP_ON_FIREFOX = env("DISABLE_CSP_ON_FIREFOX", bool, True)
DISABLE_CSP_ON_CHROME = env("DISABLE_CSP_ON_CHROME", bool, False)
# If True and --proxy=IP_ADDRESS:PORT is invalid, then error immediately.
RAISE_INVALID_PROXY_STRING_EXCEPTION = env(
    "RAISE_INVALID_PROXY_STRING_EXCEPTION", bool, True
)

# This adds wait_for_ready_state_complete() after various browser actions.
# Setting this to True may improve reliability at the cost of speed.
# Called after self.open(url) or self.open_url(url), NOT self.driver.open(url)
WAIT_FOR_RSC_ON_PAGE_LOADS = env("WAIT_FOR_RSC_ON_PAGE_LOADS", bool, True)
# Called after self.click(selector), NOT element.click()
WAIT_FOR_RSC_ON_CLICKS = env("WAIT_FOR_RSC_ON_CLICKS", bool, False)
# This adds wait_for_angularjs() after various browser actions.
# (Requires WAIT_FOR_RSC_ON_PAGE_LOADS and WAIT_FOR_RSC_ON_CLICKS to also be on.)
WAIT_FOR_ANGULARJS = env("WAIT_FOR_ANGULARJS", bool, False)

# Default time to wait after each browser action performed during Demo Mode.
# Use Demo Mode when you want others to see what your automation is doing.
# Usage: "--demo_mode". (Can be overwritten by using "--demo_sleep=TIME".)
DEFAULT_DEMO_MODE_TIMEOUT = env("DEFAULT_DEMO_MODE_TIMEOUT", float, 0.5)
