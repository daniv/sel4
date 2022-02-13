"""
    This internal plugin manages the webdriver download, configurations and instancing
    webdrivermanager classes:
    - ChromeDriverManager: for downloading and installing chromedriver (for Google Chrome).
    - GeckoDriverManager: for downloading and installing geckodriver (for Mozilla Firefox).
    - OperaChromiumDriverManager: for downloading and installing operadriver (for Chromium based Opera browsers).
    - EdgeDriverManager: for downloading and installing edgedriver (for Microsoft Edge).
    - EdgeChromiumDriverManager: for downloading and installing Edge Chromium based webdrivers
    - IeDriverManager: for downloading and installing Internet Explorer based webdrivers
"""
import os
import sys
from typing import TYPE_CHECKING

import pytest
from loguru import logger

from sel4.conf import settings
from sel4.core import constants
from sel4.core.exceptions import ImproperlyConfigured

if TYPE_CHECKING:
    from _pytest.config import Config
    from _pytest.config.argparsing import Parser


########################################################################################################################
# PYTEST PLUGINS
########################################################################################################################

# region PYTEST PLUGINS

@pytest.hookimpl(tryfirst=True)
def pytest_addoption(parser: 'Parser') -> None:
    """
     This plugin adds the following command-line options to pytest:

    --chrome  will use chrome driver
    --edge  will use edge driver
    --safari  will use safari driver
    --firefox  will use firefox driver
    --headless  (Run tests in headless mode. The default arg on Linux OS.)
    --headed, --gui  (Run tests in headed/GUI mode on Linux OS.)
    --maximize  (Start tests with the web browser window maximized.)
    --fullscreen  (Start tests with the web browser window maximized.)
    """
    from tests import colorize_option_group
    s_str = colorize_option_group('WebDriver')
    sel4_group = parser.getgroup(name='WebDriver', description=s_str)
    ctx_logger = logger.bind(task="setup".rjust(10, ' '))
    ctx_logger.debug('adding "WebDriver plugin" command-line options for [bold]pytest[/] ...')

    # region --chrome
    sel4_group.addoption(
        '--chrome',
        action='store_true',
        dest='use_chrome',
        default=False,
        help="""Will use Google Chrome""",
    )
    # endregion --chrome

    # region --edge
    sel4_group.addoption(
        "--edge",
        action="store_true",
        dest="use_edge",
        default=False,
        help="""will use Microsoft Edge.""",
    )
    # endregion --edge

    # region --safari
    sel4_group.addoption(
        "--safari",
        action="store_true",
        dest="use_safari",
        default=False,
        help="""Will use Safari web browser.""",
    )
    # endregion --safari

    # region --firefox
    sel4_group.addoption(
        "--firefox",
        action="store_true",
        dest="use_firefox",
        default=False,
        help="""will use Mozilla Firefox""",
    )
    # endregion --firefox

    # region --remote
    sel4_group.addoption(
        "--remote",
        action="store_true",
        dest="use_remote",
        default=os.getenv('REMOTE', False),
        help="""Will use remote web driver.""",
    )
    # endregion --remote

    # region --headless
    sel4_group.addoption(
        "--headless",
        action="store_true",
        dest="headless",
        default=os.getenv('HEADLESS', False),
        help="""Using this makes Webdriver run web browsers
                headless, which is required on headless machines.
                Default: False on Mac/Windows. True on Linux.""",
    )
    # endregion --headless

    # region --headed
    sel4_group.addoption(
        "--headed",
        "--gui",
        action="store_true",
        dest="headed",
        default=os.getenv('GUI', False),
        help="""Using this makes Webdriver run web browsers with
                a GUI when running tests on Linux machines.
                (The default setting on Linux is headless.)
                (The default setting on Mac or Windows is headed.)""",
    )
    # endregion --headed

    # region --maximize, --maximize-window-startup
    sel4_group.addoption(
        '--maximize',
        '--maximize-window-startup',
        action='store_true',
        dest='maximize_option',
        default=os.getenv('BROWSER_START_MAXIMIZED', True),
        help="""The option to start with the browser window maximized.""",
    )
    # endregion --maximize, --maximize-window-startup

    # region --fullscreen, --fullscreen-window-startup
    sel4_group.addoption(
        '--fullscreen', '--fullscreen-window-startup',
        action='store_true',
        dest='fullscreen_option',
        default=os.getenv('BROWSER_START_FULL_SCREEN', False),
        help="""The option to start with the browser window fullscreen.""",
    )
    # endregion --fullscreen, --fullscreen-window-startup

    parser.addini(
        name="highlights",
        type="string",
        default="2",
        help="""The default number of highlight animation loops to have per call.""",
    )

    parser.addini(
        name='start_page',
        help="""Designates the starting URL for the web browser when each test begins""",
        type='string',
        default=settings.HOME_URL
    )

    ctx_logger.debug('Validating browser switches (only 1 should be supplied)')
    sys_argv = sys.argv
    browser_text = ""
    browser_list = []
    if "--chrome" in sys_argv:
        browser_text = "chrome"
        browser_list.append("chrome")
    if "--edge" in sys_argv:
        browser_text = "edge"
        browser_list.append("edge")
    if "--safari" in sys_argv:
        browser_text = "safari"
        browser_list.append("safari")
    if "--firefox" in sys_argv:
        browser_text = "firefox"
        browser_list.append("firefox")
    if "--remote" in sys_argv:
        browser_text = "remote"
        browser_list.append("remote")
    if len(browser_list) > 1:
        bl = ", ".join(browser_list)
        raise ImproperlyConfigured(
                'TOO MANY browser types were entered!'
                f'\n  \tThere were {len(browser_list)} found:  > "{bl}"'
                "\nONLY ONE default browser is allowed!, Select a single browser & try again"
        )
    parser.addini("browser_text", type="string", default=browser_text, help="The selected browser")


@pytest.mark.trylast
def pytest_configure(config: 'Config'):
    """
    Determined if we should load the webdriver plugin
    This is a pytest hook implementation
    """
    config_logger = logger.bind(task="config".rjust(10, ' '))

    # if config.getini("browser_text"):
    #     config.option.browser = session_config.browser_settings.browser_shortcut

    xvfb = config.getoption("xvfb", False)
    headed = config.getoption("headed", False)
    headless = config.getoption("headless", False)
    browser = config.getini("browser_text")

    if xvfb and "linux" not in sys.platform:
        # The Xvfb virtual display server is for Linux OS Only!
        config.option.xvfb = False
    if (
            "linux" in sys.platform
            and not headed
            and not headless
            and not xvfb
    ):
        msg = (
            "Linux uses --headless by default. "
            "To override, use --headed / --gui. "
            "For Xvfb mode instead, use --xvfb. "
            "Or hide this info with --headless."
        )
        config_logger.info(msg)
        session_config.browser_settings.headless = True
        if not headless:
            session_config.browser_settings.headed = True

    if browser == "chrome":
        from sel4.core.plugins._webdriver_downloader import ChromeDriverDownloader
        downloader = ChromeDriverDownloader(config)

        config_logger.debug('driver_name "{}"', downloader.driver_name)
        config_logger.debug('version_mode "{}"', settings.WEB_DRIVER_MANAGER_VERSION_MODE)
        config_logger.debug('latest_version {}', downloader.latest_version)
        config_logger.debug('compatible_version {}', downloader.compatible_version)
        constants.Browser.VERSION['chrome'] = downloader.compatible_version
        constants.Browser.LATEST['chrome'] = downloader.latest_version

        config_logger.debug('compressed_file_folder {}', downloader.compressed_file_folder)
        url, file = downloader.download_url
        from httpx import URL
        httpx_url = URL(url)
        httpx_url = {
            'host': httpx_url.host,
            'path': httpx_url.path,
            'params': str(httpx_url.params)
        }
        config_logger.debug('webdriver download_url \n{}', httpx_url)
        config_logger.debug('webdriver download_file {}', file)
        del httpx_url

        config_logger.info('Creating directory for "Chrome downloads" as {}', str(downloader.download_folder))
        config_logger.info('Creating directory for "Chrome extractions" as {}', str(downloader.extract_folder))
        from sel4.utils.fileutils import mkdir_p
        mkdir_p(downloader.download_folder)
        mkdir_p(downloader.extract_folder)
        downloader.install()
