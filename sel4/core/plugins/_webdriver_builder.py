import sys
from typing import TYPE_CHECKING, List, Optional

from dictor import dictor
from loguru import logger
from pydantic import BaseModel, DirectoryPath, Field, FilePath, constr

from sel4.conf import settings

from ...core import constants
from ...utils.typeutils import NoneStr

if TYPE_CHECKING:
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.edge.options import Options as EdgeOptions
    from selenium.webdriver.remote.webdriver import WebDriver


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
    browser_name = launcher.browser_name
    if browser_name == constants.Browser.FIREFOX:
        firefox_options = _set_firefox_options(
            downloads_path,
            headless,
            locale_code,
            proxy_string,
            proxy_bypass_list,
            user_agent,
            disable_csp,
            firefox_arg,
            firefox_pref,
        )
        if LOCAL_GECKODRIVER and os.path.exists(LOCAL_GECKODRIVER):
            try:
                make_driver_executable_if_not(LOCAL_GECKODRIVER)
            except Exception as e:
                logger.debug(
                    "\nWarning: Could not make geckodriver"
                    " executable: %s" % e
                )
        elif not is_geckodriver_on_path():
            args = " ".join(sys.argv)
            if not ("-n" in sys.argv or " -n=" in args or args == "-c"):
                # (Not multithreaded)
                from seleniumbase.console_scripts import sb_install

                sys_args = sys.argv  # Save a copy of current sys args
                print("\nWarning: geckodriver not found! Installing now:")
                try:
                    sb_install.main(override="geckodriver")
                except Exception as e:
                    print("\nWarning: Could not install geckodriver: %s" % e)
                sys.argv = sys_args  # Put back the original sys args
        import warnings
        warnings.simplefilter("ignore", category=DeprecationWarning)
        if "linux" in launcher.platform:
            from selenium.webdriver.common.desired_capabilities import (
                DesiredCapabilities,
            )

            firefox_capabilities = DesiredCapabilities.FIREFOX.copy()
            firefox_capabilities["marionette"] = True
            if launcher.headless:
                firefox_capabilities["moz:firefoxOptions"] = {
                    "args": ["-headless"]
                }
            return webdriver.Firefox(
                capabilities=firefox_capabilities, options=firefox_options
            )
        else:
            if os.path.exists(LOCAL_GECKODRIVER):
                service = FirefoxService(
                    executable_path=LOCAL_GECKODRIVER
                )
                return webdriver.Firefox(
                    service=service,
                    options=firefox_options,
                )
            else:
                return webdriver.Firefox(options=firefox_options)
    elif browser_name == constants.Browser.EDGE:
        prefs = {
            "download.default_directory": downloads_path,
            "local_discovery.notifications_enabled": False,
            "credentials_enable_service": False,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
            "safebrowsing.disable_download_protection": True,
            "default_content_setting_values.notifications": 0,
            "default_content_settings.popups": 0,
            "managed_default_content_settings.popups": 0,
            "content_settings.exceptions.automatic_downloads.*.setting": 1,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_settings.popups": 0,
            "profile.managed_default_content_settings.popups": 0,
            "profile.default_content_setting_values.automatic_downloads": 1,
        }
        if LOCAL_EDGEDRIVER and os.path.exists(LOCAL_EDGEDRIVER):
            try:
                make_driver_executable_if_not(LOCAL_EDGEDRIVER)
            except Exception as e:
                logger.debug(
                    "\nWarning: Could not make edgedriver"
                    " executable: %s" % e
                )
        elif not is_edgedriver_on_path():
            args = " ".join(sys.argv)
            if not ("-n" in sys.argv or " -n=" in args or args == "-c"):
                # (Not multithreaded)
                from seleniumbase.console_scripts import sb_install

                sys_args = sys.argv  # Save a copy of current sys args
                print("\nWarning: msedgedriver not found. Installing now:")
                sb_install.main(override="edgedriver")
                sys.argv = sys_args  # Put back the original sys args

        # For Microsoft Edge (Chromium) version 80 or higher
        Edge = webdriver.edge.webdriver.WebDriver
        EdgeOptions = webdriver.edge.webdriver.Options

        if LOCAL_EDGEDRIVER and os.path.exists(LOCAL_EDGEDRIVER):
            try:
                make_driver_executable_if_not(LOCAL_EDGEDRIVER)
            except Exception as e:
                logger.debug(
                    "\nWarning: Could not make edgedriver"
                    " executable: %s" % e
                )
        edge_options = EdgeOptions()
        edge_options.use_chromium = True
        if launcher.block_images:
            prefs["profile.managed_default_content_settings.images"] = 2
        if launcher.external_pdf:
            prefs["plugins.always_open_pdf_externally"] = True
        edge_options.add_experimental_option("prefs", prefs)
        edge_options.add_experimental_option("w3c", True)
        edge_options.add_argument(
            "--disable-blink-features=AutomationControlled"
        )
        edge_options.add_experimental_option(
            "useAutomationExtension", False
        )
        edge_options.add_experimental_option(
            "excludeSwitches", ["enable-automation", "enable-logging"]
        )
        if not launcher.enable_sync:
            edge_options.add_argument("--disable-sync")
        if launcher.guest_mode:
            edge_options.add_argument("--guest")
        if launcher.headless:
            edge_options.add_argument("--headless")
        if launcher.mobile_emulator:
            emulator_settings = {}
            device_metrics = {}
            if (
                    type(device_width) is int
                    and type(device_height) is int
                    and type(device_pixel_ratio) is int
            ):
                device_metrics["width"] = device_width
                device_metrics["height"] = device_height
                device_metrics["pixelRatio"] = device_pixel_ratio
            else:
                device_metrics["width"] = 411
                device_metrics["height"] = 731
                device_metrics["pixelRatio"] = 3
            emulator_settings["deviceMetrics"] = device_metrics
            if launcher.user_agent:
                emulator_settings["userAgent"] = launcher.user_agent
            edge_options.add_experimental_option(
                "mobileEmulation", emulator_settings
            )
        if launcher.user_data_dir:
            abs_path = launcher.user_data_dir.absolute()
            edge_options.add_argument(f"user-data-dir={str(abs_path)}")
        if launcher.extension_zip:
            # Can be a comma-separated list of .ZIP or .CRX files
            for extension_zip_item in launcher.extension_zip:
                abs_path = os.path.abspath(extension_zip_item)
                edge_options.add_extension(abs_path)
        if launcher.extension_dir:
            # load-extension input can be a comma-separated list
            abs_path = os.path.abspath(launcher.extension_dir)
            edge_options.add_argument("--load-extension=%s" % abs_path)
        edge_options.add_argument("--disable-infobars")
        edge_options.add_argument("--disable-notifications")
        edge_options.add_argument("--disable-save-password-bubble")
        edge_options.add_argument("--disable-single-click-autofill")
        edge_options.add_argument(
            "--disable-autofill-keyboard-accessory-view[8]"
        )
        edge_options.add_argument("--disable-translate")
        if not launcher.enable_ws:
            edge_options.add_argument("--disable-web-security")
        edge_options.add_argument("--homepage=about:blank")
        edge_options.add_argument("--dns-prefetch-disable")
        edge_options.add_argument("--dom-automation")
        edge_options.add_argument("--disable-hang-monitor")
        edge_options.add_argument("--disable-prompt-on-repost")
        if (
                settings.DISABLE_CSP_ON_CHROME or launcher.disable_csp
        ) and not launcher.headless:
            # Headless Edge doesn't support extensions, which are required
            # for disabling the Content Security Policy on Edge
            edge_options = _add_chrome_disable_csp_extension(edge_options)
        if launcher.ad_block_on and not launcher.headless:
            edge_options = _add_chrome_ad_block_extension(edge_options)
        if launcher.proxy_string:
            if proxy_auth:
                edge_options = _add_chrome_proxy_extension(
                    edge_options, proxy_string, proxy_user, proxy_pass
                )
            edge_options.add_argument("--proxy-server=%s" % proxy_string)
        if launcher.proxy_bypass_list:
            edge_options.add_argument(
                "--proxy-bypass-list=%s" % launcher.proxy_bypass_list
            )
        edge_options.add_argument("--test-type")
        edge_options.add_argument("--log-level=3")
        edge_options.add_argument("--no-first-run")
        edge_options.add_argument("--ignore-certificate-errors")
        if launcher.devtools and not launcher.headless:
            edge_options.add_argument("--auto-open-devtools-for-tabs")
        edge_options.add_argument("--allow-file-access-from-files")
        edge_options.add_argument("--allow-insecure-localhost")
        edge_options.add_argument("--allow-running-insecure-content")
        if launcher.user_agent:
            edge_options.add_argument("--user-agent=%s" % user_agent)
        edge_options.add_argument("--no-sandbox")
        if launcher.remote_debug:
            # To access the Remote Debugger, go to: http://localhost:9222
            # while a Chromium driver is running.
            # Info: https://chromedevtools.github.io/devtools-protocol/
            edge_options.add_argument("--remote-debugging-port=9222")
        if launcher.swiftshader:
            edge_options.add_argument("--use-gl=swiftshader")
        else:
            edge_options.add_argument("--disable-gpu")
        if "linux" in launcher.platform:
            edge_options.add_argument("--disable-dev-shm-usage")
        if launcher.chromium_arg:
            # Can be a comma-separated list of Chromium args
            for chromium_arg_item in launcher.chromium_arg:
                chromium_arg_item = chromium_arg_item.strip()
                if not chromium_arg_item.startswith("--"):
                    if chromium_arg_item.startswith("-"):
                        chromium_arg_item = "-" + chromium_arg_item
                    else:
                        chromium_arg_item = "--" + chromium_arg_item
                if len(chromium_arg_item) >= 3:
                    edge_options.add_argument(chromium_arg_item)
        try:
            service = EdgeService(executable_path=LOCAL_EDGEDRIVER)
            driver = Edge(service=service, options=edge_options)
        except Exception as e:
            auto_upgrade_edgedriver = False
            edge_version = None
            if "This version of MSEdgeDriver only supports" in e.msg:
                if "Current browser version is " in e.msg:
                    auto_upgrade_edgedriver = True
                    edge_version = e.msg.split(
                        "Current browser version is "
                    )[1].split(' ')[0]
                elif "only supports MSEdge version " in e.msg:
                    auto_upgrade_edgedriver = True
                    edge_version = e.msg.split(
                        "only supports MSEdge version "
                    )[1].split(' ')[0]
            if not auto_upgrade_edgedriver:
                raise Exception(e.msg)  # Not an obvious fix. Raise.
            else:
                pass  # Try upgrading EdgeDriver to match Edge.
            args = " ".join(sys.argv)
            if ("-n" in sys.argv or " -n=" in args or args == "-c"):
                import fasteners

                edgedriver_fixing_lock = fasteners.InterProcessLock(
                    constants.MultiBrowser.CHROMEDRIVER_FIXING_LOCK
                )
                with edgedriver_fixing_lock:
                    if not _was_chromedriver_repaired():  # Works for Edge
                        _repair_edgedriver(edge_version)
                        _mark_chromedriver_repaired()  # Works for Edge
            else:
                if not _was_chromedriver_repaired():  # Works for Edge
                    _repair_edgedriver(edge_version)
                _mark_chromedriver_repaired()  # Works for Edge
            service = EdgeService(executable_path=LOCAL_EDGEDRIVER)
            return Edge(service=service, options=edge_options)
    elif launcher.browser_name == constants.Browser.SAFARI:
        arg_join = " ".join(sys.argv)
        if ("-n" in sys.argv) or (" -n=" in arg_join) or (arg_join == "-c"):
            # Skip if multithreaded
            raise Exception("Can't run Safari tests in multi-threaded mode!")
        warnings.simplefilter("ignore", category=DeprecationWarning)
        return webdriver.safari.webdriver.WebDriver(quiet=False)
    elif browser_name == constants.Browser.GOOGLE_CHROME:
        logger.info("Configuring chromedriver before launch browser instance")

        local_chromedriver = get_session_settings().browser_settings.local_chromedriver
        try:
            chrome_options = set_chrome_options(launcher)
            if local_chromedriver and local_chromedriver.exists():
                try:
                    launcher.make_driver_executable_if_not()
                except Exception as e:
                    logger.debug(
                        "\nWarning: Could not make chromedriver executable: {}", e
                    )
            if not launcher.headless or "linux" not in sys.platform:
                try:
                    if local_chromedriver.exists():
                        from selenium.webdriver.chrome.service import (
                            Service as ChromeService,
                        )
                        service = ChromeService(
                            executable_path=str(local_chromedriver)
                        )
                        driver = webdriver.Chrome(
                            service=service,
                            options=chrome_options,
                        )
                    else:
                        driver = webdriver.Chrome(options=chrome_options)
                except WebDriverException as e:
                    headless = True
                    headless_options = set_chrome_options(launcher)
                    args = " ".join(sys.argv)
                    if ("-n" in sys.argv or " -n=" in args or args == "-c"):
                        import fasteners

                        chromedriver_fixing_lock = fasteners.InterProcessLock(
                            constants.MultiBrowser.CHROMEDRIVER_FIXING_LOCK
                        )
                        with chromedriver_fixing_lock:
                            if not _was_chromedriver_repaired():
                                _repair_chromedriver(
                                    chrome_options, headless_options
                                )
                                _mark_chromedriver_repaired()
                    else:
                        if not _was_chromedriver_repaired():
                            _repair_chromedriver(
                                chrome_options, headless_options
                            )
                        _mark_chromedriver_repaired()
                    if local_chromedriver.exists():
                        from selenium.webdriver.chrome.service import (
                            Service as ChromeService,
                        )
                        service = ChromeService(
                            executable_path=str(local_chromedriver)
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
                except Exception as e:
                    auto_upgrade_chromedriver = False
                    if "This version of ChromeDriver only supports" in e.msg:
                        auto_upgrade_chromedriver = True
                    elif "Chrome version must be between" in e.msg:
                        auto_upgrade_chromedriver = True
                    if auto_upgrade_chromedriver:
                        args = " ".join(sys.argv)
                        if (
                                "-n" in sys.argv
                                or " -n=" in args
                                or args == "-c"
                        ):
                            import fasteners

                            chromedr_fixing_lock = fasteners.InterProcessLock(
                                constants.MultiBrowser.CHROMEDRIVER_FIXING_LOCK
                            )
                            with chromedr_fixing_lock:
                                if not _was_chromedriver_repaired():
                                    try:
                                        _repair_chromedriver(
                                            chrome_options, chrome_options
                                        )
                                        _mark_chromedriver_repaired()
                                    except Exception:
                                        pass
                        else:
                            if not _was_chromedriver_repaired():
                                try:
                                    _repair_chromedriver(
                                        chrome_options, chrome_options
                                    )
                                except Exception:
                                    pass
                            _mark_chromedriver_repaired()
                        try:
                            return webdriver.Chrome(options=chrome_options)
                        except Exception:
                            pass
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
    else:
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
        chrome_options.add_experimental_option("useAutomationExtension", False)
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
