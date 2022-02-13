from typing import Dict

from sel4.utils.enumutils import StrEnum

MICRO_TIMEOUT: int = 1
MINI_TIMEOUT: int = 2
SMALL_TIMEOUT: int = 6
MEDIUM_TIMEOUT: int = 15
LARGE_TIMEOUT: int = 30
EXTRA_LARGE_TIMEOUT: int = 40
EXTREME_TIMEOUT: int = 60


class Environments(StrEnum):
    STAGING = "staging"
    QA = "qa"
    DEV = "dev"
    PROD = "prod"
    LOCAL = "local"

    @classmethod
    def settings(cls) -> Dict[str, str]:
        return {
            Environments.STAGING: "sel4.settings.staging",
            Environments.QA: "sel4.settings.qa",
            Environments.DEV: "sel4.settings.dev",
            Environments.PROD: "sel4.settings.prod",
            Environments.LOCAL: "sel4.settings.local",
        }

    @classmethod
    def to_options(cls):
        return "|".join(cls.to_list())


class Browser:
    GOOGLE_CHROME = "chrome"
    EDGE = "edge"
    FIREFOX = "firefox"
    INTERNET_EXPLORER = "ie"
    OPERA = "opera"
    PHANTOM_JS = "phantomjs"
    SAFARI = "safari"
    ANDROID = "android"
    IPHONE = "iphone"
    IPAD = "ipad"
    REMOTE = "remote"

    VERSION = {
        "chrome": None,
        "edge": None,
        "firefox": None,
        "ie": None,
        "opera": None,
        "phantomjs": None,
        "safari": None,
        "android": None,
        "iphone": None,
        "ipad": None,
        "remote": None,
    }

    LATEST = {
        "chrome": None,
        "edge": None,
        "firefox": None,
        "ie": None,
        "opera": None,
        "phantomjs": None,
        "safari": None,
        "android": None,
        "iphone": None,
        "ipad": None,
        "remote": None,
    }

    SETTINGS = {
        "chrome": {
            "arguments": [
                "--test-type",
                "--log-level=3",
                "--no-first-run",
                "--disable-translate",
                "--allow-file-access-from-files",
                "--allow-insecure-localhost",
                "--allow-running-insecure-content",
                "--disable-infobars",
                "--disable-notifications",
                "--disable-save-password-bubble",
                "--disable-single-click-autofill",
                "--disable-autofill-keyboard-accessory-view[8]",
                "--dns-prefetch-disable",
                "--dom-automation",
                "--disable-hang-monitor",
                "--disable-prompt-on-repost",
                "--ignore-certificate-errors",
                "--no-sandbox",
                "--homepage=about:blank",
            ],
            "experimental_options": {
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
            },
            "servicelog": None,
            "service_args": [],
        }
    }


class State(StrEnum):
    PASSED = "Passed"
    FAILED = "Failed"
    SKIPPED = "Skipped"
    UNTESTED = "Untested"
    ERROR = "Error"
    BLOCKED = "Blocked"
    DEPRECATED = "Deprecated"
