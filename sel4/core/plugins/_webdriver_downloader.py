import os
import pathlib
import sys
from abc import ABC, abstractmethod
from functools import cached_property
from typing import (
    Optional,
    Tuple,
    Type,
    TYPE_CHECKING
)
#
import urllib3
import webdrivermanager
from loguru import logger
from sel4.conf import settings
from ...utils.regex_helper import _lazy_re_compile

if TYPE_CHECKING:
    from webdrivermanager import WebDriverManagerBase
    from rich.repr import Result
    from _pytest.config import Config
#
#
urllib3.disable_warnings()
re_version_extractor = _lazy_re_compile(r'.*?([\d.]+).*?')


class DriverDownloaderBase(ABC):
    """
    The WebdriverManager package manages the webdriver download, for specific compatible version.
    also adds the driver to ``environ['PATH']``
    """

    def __init__(
            self, extract_folder: pathlib.Path, download_folder: pathlib.Path,
            manager: Type['WebDriverManagerBase']
    ):
        import logging
        logging.getLogger("requests").setLevel(logging.ERROR)
        self.extract_folder = extract_folder
        self.download_folder = download_folder
        self.driver_manager_class = manager
        p, a = self.platform_architecture
        self.driver_name = self.driver_manager_class.driver_filenames.get(p)
        self.setup_logger = logger.bind(task="setup".rjust(10, ' '))
        # self.setup_logger.debug("Current platform/architecture is {platform}/{bits}bit", platform=p, bits=a)
        # self.setup_logger.debug("download folder: {}", self.download_folder)
        # self.setup_logger.debug("sym-link folder: {}", self.extract_folder)
        # self.setup_logger.debug("sym-link file  : {}", self.driver_name)
        self._is_win = False
        self._is_linux = False
        self._is_mac = False
        self.driver_manager_inst = manager(
            download_root=self.download_folder,
            link_path=self.extract_folder,
            os_name=p, bitness=a,
        )

    @cached_property
    def platform_architecture(self) -> Tuple[str, str]:
        """ get from sys the sys.platform property and split the result to platfom and architecture
        :return: a tuple containing
        """
        if sys.platform.startswith('linux') and sys.maxsize > 2 ** 32:
            pl = 'linux'
            arch = '64'
            self._is_linux = True
        elif sys.platform == 'darwin':
            pl = 'mac'
            arch = '64'
            self._is_mac = True
        elif sys.platform.startswith('win'):
            pl = 'win'
            arch = '32'
            self._is_win = True
        else:
            raise RuntimeError('Could not determine chromedriver download URL for this platform.')
        return pl, arch

    @property
    def download_root(self) -> pathlib.Path:
        """ Returns the location of webdriver is downloaded """
        return pathlib.Path(self.driver_manager_inst.download_root)

    @cached_property
    def latest_version(self) -> str:
        """ Returns the latest version of chromedriver """
        return self.driver_manager_inst.get_latest_version()

    @cached_property
    def compatible_version(self) -> str:
        """ Returns the compatible version compared to Google Chrome installation """
        return self.driver_manager_inst.get_compatible_version()

    @cached_property
    def compressed_file_folder(self) -> pathlib.Path:
        """
        Method for getting the download path for a web driver binary.

        :returns: The download path of the web driver binary.
        """
        version = settings.WEB_DRIVER_MANAGER_VERSION_MODE
        return pathlib.Path(self.driver_manager_inst.get_download_path(version))

    @cached_property
    def download_url(self) -> Tuple[str, str]:
        """
        Method for getting the download URL for a web driver binary.

        :returns: The download URL for the web driver binary.
        """
        version = settings.WEB_DRIVER_MANAGER_VERSION_MODE
        return self.driver_manager_inst.get_download_url(version=version)

    @property
    def fallback_url(self) -> Optional[str]:
        url = self.driver_manager_inst.fallback_url
        if url:
            return url

    @abstractmethod
    def is_webdriver_on_path(self) -> bool:
        ...

    def need_to_download_driver(self, executable: pathlib.Path) -> bool:
        """ Determines if a new fresh chrome driver needs to be downloaded """
        from packaging.version import parse
        try:
            import subprocess
            req = parse(self.compatible_version)
            version = subprocess.check_output([str(executable), '-v'])
            import re
            version = re_version_extractor.match(version.decode('utf-8'))[1]
            actual = parse(version)
            if actual.major == req.major and actual.minor == req.minor and actual.micro == req.micro:
                return False
        except Exception:
            self.setup_logger.opt(exception=True).info("sym-link file  : {}", self.driver_name)
            return True
        return True

    def download_and_install(self) -> Tuple[pathlib.Path, pathlib.Path]:
        """
        Method for downloading a web driver binary, extracting it into the download directory and creating a symlink
        to the binary in the link directory.
        """
        download_and_install = self.driver_manager_inst.download_and_install(
            version=settings.WEB_DRIVER_MANAGER_VERSION_MODE,
            show_progress_bar=settings.WEB_DRIVER_MANAGER_SHOW_PROGRESS
        )
        return pathlib.Path(download_and_install[0]), pathlib.Path(download_and_install[1])

    def __rich_repr__(self) -> "Result":
        yield self.driver_name
        yield "version_mode", settings.WEB_DRIVER_MANAGER_VERSION_MODE
        yield "download_root", str(self.download_root)
        yield "latest_version", self.latest_version
        yield "compatible_version", self.compatible_version
        yield "compressed_file_folder", str(self.compressed_file_folder)
        url, file = self.download_url
        yield "download_url", str(url)
        yield "download_file", file
        yield "fallback_url", self.fallback_url, "N/A"


class ChromeDriverDownloader(DriverDownloaderBase):
    def __init__(self, config: 'Config'):
        paths = dict(settings.WEBDRIVER_MANAGER_PATHS)
        download_folder: pathlib.Path = paths.get('downloads')
        extract_folder: pathlib.Path = paths.get('executables').joinpath('chrome')
        super().__init__(extract_folder, download_folder, webdrivermanager.ChromeDriverManager)

        config.addinivalue_line('used_packs', webdrivermanager.get_version())

    def install(self):
        try:
            self._install_chrome_webdriver()
            if not self.is_webdriver_on_path():
                args = " ".join(sys.argv)
                if not ("-n" in sys.argv or " -n=" in args or args == "-c"):
                    self.add_chrome_to_environment_path()
                    assert self.is_webdriver_on_path()
        except (NotImplementedError, RuntimeError) as e:
            self.setup_logger.exception(str(e))
            raise

    def _install_chrome_webdriver(self):
        """ install the webdriver, if required it will download from chrome URL"""

        do_install = True
        executable = self.extract_folder.joinpath(self.driver_name)
        from sel4.core import runtime
        runtime.local_chromedriver = executable
        if executable.exists() and executable.is_symlink():
            # -- determine if a new webdriver installation is required
            self.setup_logger.info('Validating current version of: {}', self.driver_name)
            do_install = self.need_to_download_driver(executable)
        if do_install:
            self.setup_logger.info('WebDriver plugin needs to '
                                   'download and install binary webdriver on /chrome/chromedriver')
            executable.unlink(missing_ok=True)
            self.setup_logger.info(
                'Downloading chrome webdriver from: {}', webdrivermanager.ChromeDriverManager.chrome_driver_base_url
            )
            downloaded_file, symlink_file = self.download_and_install()
            self.setup_logger.info('Executable file was copied to: {}', symlink_file)

    def is_webdriver_on_path(self) -> bool:
        paths = os.environ["PATH"].split(os.pathsep)
        for path in paths:
            if (not self._is_win) and os.path.exists(f'{path}/{self.driver_name}'):
                return True
            elif self._is_win and os.path.exists(f'{path}/{self.driver_name}'):
                return True
        return False

    def add_chrome_to_environment_path(self):
        """ Adds chromedriver to `os.environ[PATH]` """
        bin_folder_str = str(self.extract_folder)
        path_separator = ':'
        if sys.platform.startswith('win'):
            path_separator = ';'
        if 'PATH' not in os.environ:
            os.environ.setdefault('PATH', bin_folder_str)
        elif bin_folder_str not in os.environ['PATH']:
            env_path = f'{bin_folder_str}{path_separator}{os.environ.get("PATH")}'
            os.environ['PATH'] = env_path


class GeckoDriverDownloader(DriverDownloaderBase):

    def __init__(self):
        paths = dict(settings.WEBDRIVER_MANAGER_PATHS)
        download_folder: pathlib.Path = paths.get('downloads')
        extract_folder: pathlib.Path = paths.get('executables').joinpath('gecko')
        super().__init__(extract_folder, download_folder, webdrivermanager.ChromeDriverManager)

        from sel4.core import runtime
        pytestconfig = getattr(runtime, "pytestconfig")
        pytestconfig.addinivalue_line('used_packs', webdrivermanager.get_version())

    def _install_gecko_webdriver(self):
        """ install the webdriver, if required it will download from chrome URL"""

        do_install = True
        executable = self.extract_folder.joinpath(self.driver_name)
        setattr(kiru_config, "gecko_executable", executable)
        if executable.exists() and executable.is_symlink():
            # -- determine if a new webdriver installation is required
            self.setup_logger.info('Validating current version of: {}', self.driver_name)
            do_install = self.need_to_download_driver(executable)
        if do_install:
            self.setup_logger.info('WebDriver plugin needs to '
                                   'download and install binary webdriver on /gecko/geckodriver')
            executable.unlink(missing_ok=True)
            self.setup_logger.info(
                'Downloading gecko webdriver from: {}', webdrivermanager.GeckoDriverManager.chrome_driver_base_url
            )
            downloaded_file, symlink_file = self.download_and_install()
            self.setup_logger.info('Executable file was copied to: {}', symlink_file)

    def install(self):
        try:
            self._install_gecko_webdriver()
            if not self.is_webdriver_on_path():
                args = " ".join(sys.argv)
                if not ("-n" in sys.argv or " -n=" in args or args == "-c"):
                    self.add_chrome_to_environment_path()
                    assert self.is_webdriver_on_path()
        except (NotImplementedError, RuntimeError) as e:
            self.setup_logger.exception(str(e))
            raise

    def is_webdriver_on_path(self) -> bool:
        pass


