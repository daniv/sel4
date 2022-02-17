import os
import pathlib
import sys
from enum import unique
from typing import TYPE_CHECKING, List, Optional

from dictor import dictor
from loguru import logger
from pydantic import BaseModel, DirectoryPath, Field, FilePath, constr

from sel4.conf import settings

from ...core import constants
from ...utils.enumutils import IntEnum
from ...utils.typeutils import NoneStr

if TYPE_CHECKING:
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.edge.options import Options as EdgeOptions
    from selenium.webdriver.remote.webdriver import WebDriver


@unique
class BrowserLogLevel(IntEnum):
    """options.add_argument('--log-level=1')"""
    INFO = 0
    WARNING = 1
    LOG_ERROR = 2
    LOG_FATAL = 3


class WebDriverBrowserLauncher(BaseModel):
    browser_name: settings.SUPPORTED_BROWSERS
    headless: bool
    use_grid: bool
    devtools: bool
    incognito: bool
    guest_mode: bool
    user_agent: NoneStr
    enable_ws: bool
    enable_sync: bool
    disable_csp: bool
    mobile_emulator: bool
    ad_block_on: bool
    block_images: bool
    remote_debug: bool
    external_pdf: bool
    swiftshader: bool
    use_auto_ext: bool
    servername: NoneStr
    proxy_auth: NoneStr
    chromium_arg: List[constr(regex=r"--\w+")] = Field(default_factory=list)
    proxy_string: NoneStr
    # protocol: constants.Protocol = constants.Protocol.HTTPS
    user_data_dir: Optional[DirectoryPath]
    extension_dir: Optional[DirectoryPath]
    extension_zip: List[FilePath] = Field(default_factory=list)
    driver_path: Optional[FilePath] = None

    def make_driver_executable_if_not(self):
        driver_path = pathlib.Path(self.driver_path)
        permissions = oct(os.stat(driver_path)[0])[-3:]
        if "4" in permissions or "6" in permissions:
            # We want at least a '5' or '7' to make sure it's executable
            mode = os.stat(driver_path).st_mode
            mode |= (mode & 0o444) >> 2  # copy R bits to X
            os.chmod(driver_path, mode)


def get_driver(launcher: WebDriverBrowserLauncher) -> 'WebDriver':
    if launcher.use_grid:
        pass
    else:
        return get_local_driver(launcher)


def get_local_driver(launcher: WebDriverBrowserLauncher) -> 'WebDriver':
    """
    Spins up a new web browser and returns the driver.
    Can also be used to spin up additional browsers for the same test.
    """
    from selenium import webdriver
    from selenium.common.exceptions import WebDriverException
    match launcher.browser_name:
        case constants.Browser.FIREFOX:
            ...

        case constants.Browser.EDGE:
            ...

        case constants.Browser.SAFARI:
            ...

        case constants.Browser.GOOGLE_CHROME:
            logger.info("Configuring chromedriver before launch browser instance")

            def set_executable_driver_path():
                from webdrivermanager import ChromeDriverManager
                if sys.platform.startswith("win"):
                    executable = ChromeDriverManager.driver_filenames["win"]
                elif sys.platform.startswith("darwin"):
                    executable = ChromeDriverManager.driver_filenames["mac"]
                else:
                    executable = ChromeDriverManager.driver_filenames["linux"]
                executables: pathlib.Path = dict(settings.WEBDRIVER_MANAGER_PATHS).get("executables")
                local_chromedriver = executables.joinpath("chrome", executable)
                launcher.driver_path = local_chromedriver

            try:
                set_executable_driver_path()
                chrome_options = set_chrome_options(launcher)
                if launcher.driver_path:
                    try:
                        launcher.make_driver_executable_if_not()
                    except Exception as e:
                        logger.debug(
                            "\nWarning: Could not make chromedriver executable: {}", e
                        )
                if not launcher.headless or "linux" not in sys.platform:
                    try:
                        log_folder: pathlib.Path = dict(settings.PROJECT_PATHS).get("LOGS")
                        service_log = log_folder.joinpath("chrome_service.log")
                        from selenium.webdriver.chrome.service import Service
                        service = Service(
                            executable_path=str(launcher.driver_path),
                            log_path=str(service_log)
                        )
                        driver = webdriver.Chrome(
                            chrome_options=chrome_options,
                            service=service
                        )

                    except WebDriverException as e:
                        headless = True
                        headless_options = set_chrome_options(launcher)
                        args = " ".join(sys.argv)
                        if ("-n" in sys.argv or " -n=" in args or args == "-c"):
                            ...
                        else:
                            ...
                        if launcher.driver_path.exists():
                            from selenium.webdriver.chrome.service import (
                                Service as ChromeService,
                            )
                            service = ChromeService(
                                executable_path=str(launcher.driver_path)
                            )
                            driver = webdriver.Chrome(
                                service=service,
                                options=chrome_options,
                            )
                        else:
                            driver = webdriver.Chrome(options=chrome_options)
                    return driver
                else:  # Running headless on Linux
                    try:
                        return webdriver.Chrome(options=chrome_options)
                    except WebDriverException as e:
                        # Use the virtual display on Linux during headless errors
                        logger.debug(
                            "\nWarning: Chrome failed to launch in"
                            " headless mode. Attempting to use the"
                            " SeleniumBase virtual display on Linux..."
                        )
                        chrome_options.headless = False
                        return webdriver.Chrome(options=chrome_options)
            except WebDriverException as e:
                logger.exception(e)
                return webdriver.Chrome()
        case _:
            raise Exception(
                "%s is not a valid browser option for this system!" % browser_name
            )


def set_chrome_options(launcher: WebDriverBrowserLauncher) -> "ChromeOptions":
    from selenium import webdriver
    chrome_options = webdriver.ChromeOptions()
    chrome_settings = constants.Browser.SETTINGS.get("chrome")
    browser_name = launcher.browser_name
    preferences = dictor(chrome_settings, "experimental_options", checknone=True)
    preferences.setdefault(
        "download.default_directory", str(
            dictor(
                dict(settings.PROJECT_PATHS), "downloads", checknone=True, ignorecase=True
            )
        )
    )
    if launcher.block_images:
        preferences.setdefault("profile.managed_default_content_settings.images", 2)
    if launcher.external_pdf:
        preferences.setdefault("plugins.always_open_pdf_externally", True)
    chrome_options.add_experimental_option("prefs", preferences)
    chrome_options.add_experimental_option("w3c", True)
    if launcher.enable_sync:
        chrome_options.add_experimental_option(
            "excludeSwitches",
            ["enable-automation", "enable-logging", "disable-sync"],
        )
        chrome_options.add_argument("--enable-sync")
    else:
        chrome_options.add_experimental_option(
            "excludeSwitches",
            ["enable-automation", "enable-logging", "enable-blink-features"],
        )
    if browser_name == constants.Browser.OPERA:
        # Disable the Blink features
        if launcher.enable_sync:
            chrome_options.add_experimental_option(
                "excludeSwitches",
                (
                    [
                        "enable-automation",
                        "enable-logging",
                        "disable-sync",
                        "enable-blink-features",
                    ]
                ),
            )
            chrome_options.add_argument("--enable-sync")
        else:
            chrome_options.add_experimental_option(
                "excludeSwitches",
                (
                    [
                        "enable-automation",
                        "enable-logging",
                        "enable-blink-features",
                    ]
                ),
            )
    if launcher.mobile_emulator:
        emulator_settings = {}
        device_metrics = {}
        if (
                type(launcher.device_width) is int
                and type(launcher.device_height) is int
                and type(launcher.device_pixel_ratio) is int
        ):
            device_metrics["width"] = launcher.device_width
            device_metrics["height"] = launcher.device_height
            device_metrics["pixelRatio"] = launcher.device_pixel_ratio
        else:
            device_metrics["width"] = 411
            device_metrics["height"] = 731
            device_metrics["pixelRatio"] = 3
        emulator_settings["deviceMetrics"] = device_metrics
        if launcher.user_agent:
            emulator_settings["userAgent"] = launcher.user_agent
        chrome_options.add_experimental_option(
            "mobileEmulation", emulator_settings
        )
    if (
            not launcher.proxy_auth
            and not launcher.disable_csp
            and not launcher.ad_block_on
            and (not launcher.extension_zip and not launcher.extension_dir)
    ):
        if launcher.incognito:
            # Use Chrome's Incognito Mode
            # Incognito Mode prevents Chrome extensions from loading,
            # so if using extensions or a feature that uses extensions,
            # then Chrome's Incognito mode will be disabled instead.
            chrome_options.add_argument("--incognito")
        elif launcher.guest_mode:
            # Use Chrome's Guest Mode
            # Guest mode prevents Chrome extensions from loading,
            # so if using extensions or a feature that uses extensions,
            # then Chrome's Guest Mode will be disabled instead.
            chrome_options.add_argument("--guest")
        else:
            pass
    if launcher.user_data_dir:
        abs_path = os.path.abspath(launcher.user_data_dir)
        chrome_options.add_argument(f"user-data-dir={abs_path}")
    if len(launcher.extension_zip):
        # Can be a comma-separated list of .ZIP or .CRX files
        extension_zip_list = launcher.extension_zip.split(",")
        for extension_zip_item in extension_zip_list:
            abs_path = os.path.abspath(extension_zip_item)
            chrome_options.add_extension(abs_path)
    if launcher.extension_dir:
        # load-extension input can be a comma-separated list
        abs_path = launcher.extension_dir.absolute()
        chrome_options.add_argument("--load-extension=%s" % abs_path)

    arguments = dictor(chrome_settings, "arguments", checknone=True)
    for arg in arguments:
        chrome_options.add_argument(arg)
    if launcher.devtools and not launcher.headless:
        chrome_options.add_argument("--auto-open-devtools-for-tabs")
    if launcher.user_agent:
        chrome_options.add_argument("--user-agent=%s" % launcher.user_agent)

    # chrome_options.add_argument("--homepage=about:blank")
    if launcher.servername and launcher.servername != "localhost":
        use_auto_ext = True  # Use Automation Extension with the Selenium Grid
    if not launcher.use_auto_ext:  # Disable Automation Extension / detection. (Default)
        if browser_name != constants.Browser.OPERA:
            chrome_options.add_argument(
                "--disable-blink-features=AutomationControlled"
            )
        # -- This option is deprecated:
        # -- chrome_options.add_experimental_option("useAutomationExtension", False)
    if (settings.DISABLE_CSP_ON_CHROME or launcher.disable_csp) and not launcher.headless:
        # Headless Chrome does not support extensions, which are required
        # for disabling the Content Security Policy on Chrome.
        chrome_options = _add_chrome_disable_csp_extension(chrome_options)
    if launcher.ad_block_on and not launcher.headless:
        # Headless Chrome does not support extensions.
        chrome_options = _add_chrome_ad_block_extension(chrome_options)
    if launcher.proxy_string:
        if launcher.proxy_auth:
            chrome_options = _add_chrome_proxy_extension(
                chrome_options, launcher.proxy_string, launcher.proxy_user, launcher.proxy_pass
            )
        chrome_options.add_argument("--proxy-server=%s" % launcher.proxy_string)
        if launcher.proxy_bypass_list:
            chrome_options.add_argument(
                "--proxy-bypass-list=%s" % launcher.proxy_bypass_list
            )
    if launcher.headless:
        if not launcher.proxy_auth and not browser_name == constants.Browser.OPERA:
            # Headless Chrome doesn't support extensions, which are
            # required when using a proxy server that has authentication.
            # Instead, base_case.py will use PyVirtualDisplay when not
            # using Chrome's built-in headless mode. See link for details:
            # https://bugs.chromium.org/p/chromium/issues/detail?id=706008
            # Also, Opera Chromium doesn't support headless mode:
            # https://github.com/operasoftware/operachromiumdriver/issues/62
            chrome_options.add_argument("--headless")
    if browser_name != constants.Browser.OPERA:
        # Opera Chromium doesn't support these switches
        chrome_options.add_argument("--ignore-certificate-errors")
        if not launcher.enable_ws:
            chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--no-sandbox")
    else:
        # Opera Chromium only!
        chrome_options.add_argument("--allow-elevated-browser")
    if launcher.remote_debug:
        # To access the Remote Debugger, go to: http://localhost:9222
        # while a Chromium driver is running.
        # Info: https://chromedevtools.github.io/devtools-protocol/
        chrome_options.add_argument("--remote-debugging-port=9222")
    if launcher.swiftshader:
        chrome_options.add_argument("--use-gl=swiftshader")
    else:
        chrome_options.add_argument("--disable-gpu")
    if "linux" in sys.platform:
        chrome_options.add_argument("--disable-dev-shm-usage")
    if len(launcher.chromium_arg):
        # Can be a comma-separated list of Chromium args
        chromium_arg_list = launcher.chromium_arg.split(",")
        for chromium_arg_item in chromium_arg_list:
            chromium_arg_item = chromium_arg_item.strip()
            if not chromium_arg_item.startswith("--"):
                if chromium_arg_item.startswith("-"):
                    chromium_arg_item = "-" + chromium_arg_item
                else:
                    chromium_arg_item = "--" + chromium_arg_item
            if len(chromium_arg_item) >= 3:
                chrome_options.add_argument(chromium_arg_item)
    return chrome_options
