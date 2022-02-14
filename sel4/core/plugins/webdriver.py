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

from loguru import logger
from pytest import StashKey, hookimpl, mark
from selenium.webdriver.chrome.webdriver import WebDriver

from sel4.conf import settings

from ..exceptions import ImproperlyConfigured
from ..runtime import runtime_store

if TYPE_CHECKING:
    from pytest import Config, Parser


########################################################################################################################
# PYTEST PLUGINS
########################################################################################################################

# region PYTEST PLUGINS


@hookimpl(tryfirst=True)
def pytest_addoption(parser: "Parser") -> None:
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

    s_str = colorize_option_group("WebDriver")
    sel4_group = parser.getgroup(name="WebDriver", description=s_str)
    ctx_logger = logger.bind(task="setup".rjust(10, " "))
    ctx_logger.debug(
        'adding "WebDriver plugin" command-line options for [bold]pytest[/] ...'
    )

    # region --chrome
    sel4_group.addoption(
        "--chrome",
        action="store_true",
        dest="use_chrome",
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
        default=os.getenv("REMOTE", False),
        help="""Will use remote web driver.""",
    )
    # endregion --remote

    # region --headless
    sel4_group.addoption(
        "--headless",
        action="store_true",
        dest="headless",
        default=os.getenv("HEADLESS", False),
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
        default=os.getenv("GUI", False),
        help="""Using this makes Webdriver run web browsers with
                a GUI when running tests on Linux machines.
                (The default setting on Linux is headless.)
                (The default setting on Mac or Windows is headed.)""",
    )
    # endregion --headed

    # region --maximize, --maximize-window-startup
    sel4_group.addoption(
        "--maximize",
        "--maximize-window-startup",
        action="store_true",
        dest="maximize_option",
        default=os.getenv("BROWSER_START_MAXIMIZED", True),
        help="""The option to start with the browser window maximized.""",
    )
    # endregion --maximize, --maximize-window-startup

    # region --fullscreen, --fullscreen-window-startup
    sel4_group.addoption(
        "--fullscreen",
        "--fullscreen-window-startup",
        action="store_true",
        dest="fullscreen_option",
        default=os.getenv("BROWSER_START_FULL_SCREEN", False),
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
        name="start_page",
        help="""Designates the starting URL for the web browser when each test begins""",
        type="string",
        default=settings.HOME_URL,
    )

    ctx_logger.debug("Validating browser switches (only 1 should be supplied)")
    browser_text = ""
    sys_argv = sys.argv
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
            "TOO MANY browser types were entered!"
            f'\n  \tThere were {len(browser_list)} found:  > "{bl}"'
            "\nONLY ONE default browser is allowed!, Select a single browser & try again"
        )
    parser.addini(
        "browser_text", type="string", default=browser_text, help="The selected browser"
    )


@mark.trylast
def pytest_configure(config: "Config"):
    """
    Determined if we should load the webdriver plugin
    This is a pytest hook implementation
    """
    config_logger = logger.bind(task="config".rjust(10, " "))

    """ This runs after command-line options have been parsed. """
    # sb_config.item_count = 0
    # sb_config.item_count_passed = 0
    # sb_config.item_count_failed = 0
    # sb_config.item_count_skipped = 0
    # sb_config.item_count_untested = 0
    # sb_config.is_pytest = True
    # sb_config.pytest_config = config
    # sb_config.browser = config.getoption("browser")
    # if sb_config._browser_shortcut:
    #     sb_config.browser = sb_config._browser_shortcut
    # sb_config.account = config.getoption("account")
    # sb_config.data = config.getoption("data")
    # sb_config.var1 = config.getoption("var1")
    # sb_config.var2 = config.getoption("var2")
    # sb_config.var3 = config.getoption("var3")
    # sb_config.environment = config.getoption("environment")
    # sb_config.with_selenium = config.getoption("with_selenium")
    # sb_config.user_agent = config.getoption("user_agent")
    # sb_config.mobile_emulator = config.getoption("mobile_emulator")
    # sb_config.device_metrics = config.getoption("device_metrics")
    # sb_config.headless = config.getoption("headless")
    # sb_config.headed = config.getoption("headed")
    # sb_config.xvfb = config.getoption("xvfb")
    # sb_config.locale_code = config.getoption("locale_code")
    # sb_config.interval = config.getoption("interval")
    # sb_config.start_page = config.getoption("start_page")
    # sb_config.chromium_arg = config.getoption("chromium_arg")
    # sb_config.firefox_arg = config.getoption("firefox_arg")
    # sb_config.firefox_pref = config.getoption("firefox_pref")
    # sb_config.extension_zip = config.getoption("extension_zip")
    # sb_config.extension_dir = config.getoption("extension_dir")
    # sb_config.with_testing_base = config.getoption("with_testing_base")
    # sb_config.with_db_reporting = config.getoption("with_db_reporting")
    # sb_config.with_s3_logging = config.getoption("with_s3_logging")
    # sb_config.with_screen_shots = config.getoption("with_screen_shots")
    # sb_config.with_basic_test_info = config.getoption("with_basic_test_info")
    # sb_config.with_page_source = config.getoption("with_page_source")
    # sb_config.protocol = config.getoption("protocol")
    # sb_config.servername = config.getoption("servername")
    # sb_config.port = config.getoption("port")
    # if sb_config.servername != "localhost":
    #     # Using Selenium Grid
    #     # (Set --server="127.0.0.1" for localhost Grid)
    #     if str(sb_config.port) == "443":
    #         sb_config.protocol = "https"
    # sb_config.proxy_string = config.getoption("proxy_string")
    # sb_config.proxy_bypass_list = config.getoption("proxy_bypass_list")
    # sb_config.cap_file = config.getoption("cap_file")
    # sb_config.cap_string = config.getoption("cap_string")
    # sb_config.settings_file = config.getoption("settings_file")
    # sb_config.user_data_dir = config.getoption("user_data_dir")
    # sb_config.database_env = config.getoption("database_env")
    # sb_config.log_path = "latest_logs/"  # (No longer editable!)
    # sb_config.archive_logs = config.getoption("archive_logs")
    # if config.getoption("archive_downloads"):
    #     settings.ARCHIVE_EXISTING_DOWNLOADS = True
    # sb_config._time_limit = config.getoption("time_limit")
    # sb_config.time_limit = config.getoption("time_limit")
    # sb_config.slow_mode = config.getoption("slow_mode")
    # sb_config.demo_mode = config.getoption("demo_mode")
    # sb_config.demo_sleep = config.getoption("demo_sleep")
    # sb_config.highlights = config.getoption("highlights")
    # sb_config.message_duration = config.getoption("message_duration")
    # sb_config.js_checking_on = config.getoption("js_checking_on")
    # sb_config.ad_block_on = config.getoption("ad_block_on")
    # sb_config.block_images = config.getoption("block_images")
    # sb_config.verify_delay = config.getoption("verify_delay")
    # sb_config.recorder_mode = config.getoption("recorder_mode")
    # sb_config.recorder_ext = config.getoption("recorder_mode")  # Again
    # sb_config.disable_csp = config.getoption("disable_csp")
    # sb_config.disable_ws = config.getoption("disable_ws")
    # sb_config.enable_ws = config.getoption("enable_ws")
    # if not sb_config.disable_ws:
    #     sb_config.enable_ws = True
    # sb_config.enable_sync = config.getoption("enable_sync")
    # sb_config.use_auto_ext = config.getoption("use_auto_ext")
    # sb_config.no_sandbox = config.getoption("no_sandbox")
    # sb_config.disable_gpu = config.getoption("disable_gpu")
    # sb_config.remote_debug = config.getoption("remote_debug")
    # sb_config.dashboard = config.getoption("dashboard")
    # sb_config.swiftshader = config.getoption("swiftshader")
    # sb_config.incognito = config.getoption("incognito")
    # sb_config.guest_mode = config.getoption("guest_mode")
    # sb_config.devtools = config.getoption("devtools")
    # sb_config.reuse_session = config.getoption("reuse_session")
    # sb_config.crumbs = config.getoption("crumbs")
    from sel4.core.runtime import shared_driver
    config_logger.debug("Setting StashKey[WebDriver] for shared_driver to None")
    runtime_store[shared_driver] = None
    # sb_config.maximize_option = config.getoption("maximize_option")
    # sb_config.save_screenshot = config.getoption("save_screenshot")
    # sb_config.visual_baseline = config.getoption("visual_baseline")
    # sb_config.external_pdf = config.getoption("external_pdf")
    # sb_config.timeout_multiplier = config.getoption("timeout_multiplier")
    # sb_config._is_timeout_changed = False
    # sb_config._SMALL_TIMEOUT = settings.SMALL_TIMEOUT
    # sb_config._LARGE_TIMEOUT = settings.LARGE_TIMEOUT
    # sb_config.pytest_html_report = config.getoption("htmlpath")  # --html=FILE
    # sb_config._sb_node = {}  # sb node dictionary (Used with the sb fixture)
    # # Dashboard-specific variables
    # sb_config._results = {}  # SBase Dashboard test results
    # sb_config._duration = {}  # SBase Dashboard test duration
    # sb_config._display_id = {}  # SBase Dashboard display ID
    # sb_config._d_t_log_path = {}  # SBase Dashboard test log path
    # sb_config._dash_html = None  # SBase Dashboard HTML copy
    # sb_config._test_id = None  # SBase Dashboard test id
    # sb_config._latest_display_id = None  # The latest SBase display id
    # sb_config._dashboard_initialized = False  # Becomes True after init
    # sb_config._has_exception = False  # This becomes True if any test fails
    # sb_config._multithreaded = False  # This becomes True if multithreading
    # sb_config._only_unittest = True  # If any test uses BaseCase, becomes False
    # sb_config._sbase_detected = False  # Becomes True during SeleniumBase tests
    # sb_config._extra_dash_entries = []  # Dashboard entries for non-SBase tests
    # sb_config._using_html_report = False  # Becomes True when using html report
    # sb_config._dash_is_html_report = False  # Dashboard becomes the html report
    # sb_config._saved_dashboard_pie = None  # Copy of pie chart for html report
    # sb_config._dash_final_summary = None  # Dash status to add to html report
    # sb_config._html_report_name = None  # The name of the pytest html report
    #
    # arg_join = " ".join(sys.argv)
    # if ("-n" in sys.argv) or (" -n=" in arg_join) or ("-c" in sys.argv):
    #     sb_config._multithreaded = True
    # if "--html" in sys.argv or " --html=" in arg_join:
    #     sb_config._using_html_report = True
    #     sb_config._html_report_name = config.getoption("htmlpath")
    #     if sb_config.dashboard:
    #         if sb_config._html_report_name == "dashboard.html":
    #             sb_config._dash_is_html_report = True
    #
    # if sb_config.xvfb and "linux" not in sys.platform:
    #     # The Xvfb virtual display server is for Linux OS Only!
    #     sb_config.xvfb = False
    # if (
    #         "linux" in sys.platform
    #         and not sb_config.headed
    #         and not sb_config.headless
    #         and not sb_config.xvfb
    # ):
    #     print(
    #         "(Linux uses --headless by default. "
    #         "To override, use --headed / --gui. "
    #         "For Xvfb mode instead, use --xvfb. "
    #         "Or hide this info with --headless.)"
    #     )
    #     sb_config.headless = True
    # if not sb_config.headless:
    #     sb_config.headed = True
    #
    # if sb_config._multithreaded:
    #     if config.getoption("use_chrome"):
    #         sb_config.browser = "chrome"
    #     elif config.getoption("use_edge"):
    #         sb_config.browser = "edge"
    #     elif config.getoption("use_firefox"):
    #         sb_config.browser = "firefox"
    #     elif config.getoption("use_ie"):
    #         sb_config.browser = "ie"
    #     elif config.getoption("use_opera"):
    #         sb_config.browser = "opera"
    #     elif config.getoption("use_safari"):
    #         sb_config.browser = "safari"
    #     else:
    #         pass  # Use the browser specified using "--browser=BROWSER"
    #
    # from seleniumbase.core import log_helper
    # from seleniumbase.core import download_helper
    # from seleniumbase.core import proxy_helper
    #
    # log_helper.log_folder_setup(sb_config.log_path, sb_config.archive_logs)
    # download_helper.reset_downloads_folder()
    # proxy_helper.remove_proxy_zip_if_present()

    # xvfb = config.getoption("xvfb", False)
    # headed = config.getoption("headed", False)
    # headless = config.getoption("headless", False)
    # browser_text = config.getini("browser_text")
    #
    # if xvfb and "linux" not in sys.platform:
    #     # The Xvfb virtual display server is for Linux OS Only!
    #     config.option.xvfb = False
    # if (
    #         "linux" in sys.platform
    #         and not headed
    #         and not headless
    #         and not xvfb
    # ):
    #     msg = (
    #         "Linux uses --headless by default. "
    #         "To override, use --headed / --gui. "
    #         "For Xvfb mode instead, use --xvfb. "
    #         "Or hide this info with --headless."
    #     )
    #     config_logger.info(msg)
    #     session_config.browser_settings.headless = True
    #     if not headless:
    #         session_config.browser_settings.headed = True
    #
    # if browser == "chrome":
    #     from sel4.core.plugins._webdriver_downloader import ChromeDriverDownloader
    #     downloader = ChromeDriverDownloader(config)
    #
    #     config_logger.debug('driver_name "{}"', downloader.driver_name)
    #     config_logger.debug('version_mode "{}"', settings.WEB_DRIVER_MANAGER_VERSION_MODE)
    #     config_logger.debug('latest_version {}', downloader.latest_version)
    #     config_logger.debug('compatible_version {}', downloader.compatible_version)
    #     constants.Browser.VERSION['chrome'] = downloader.compatible_version
    #     constants.Browser.LATEST['chrome'] = downloader.latest_version
    #
    #     config_logger.debug('compressed_file_folder {}', downloader.compressed_file_folder)
    #     url, file = downloader.download_url
    #     from httpx import URL
    #     httpx_url = URL(url)
    #     httpx_url = {
    #         'host': httpx_url.host,
    #         'path': httpx_url.path,
    #         'params': str(httpx_url.params)
    #     }
    #     config_logger.debug('webdriver download_url \n{}', httpx_url)
    #     config_logger.debug('webdriver download_file {}', file)
    #     del httpx_url
    #
    #     config_logger.info('Creating directory for "Chrome downloads" as {}', str(downloader.download_folder))
    #     config_logger.info('Creating directory for "Chrome extractions" as {}', str(downloader.extract_folder))
    #     from sel4.utils.fileutils import mkdir_p
    #     mkdir_p(downloader.download_folder)
    #     mkdir_p(downloader.extract_folder)
    #     downloader.install()
