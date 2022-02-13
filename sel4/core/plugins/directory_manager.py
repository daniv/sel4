import os
import pathlib
from datetime import date
from typing import TYPE_CHECKING, Optional, List

import pytest
from _pytest.pathlib import rm_rf
from loguru import logger

from sel4.utils.fileutils import mkdir_p

if TYPE_CHECKING:
    from _pytest.config import Config


class DirectoryManagerHooks:
    def pytest_archive_results(self):
        """ Creates the last results directory """

    def pytest_create_results_directory(self):
        """ Creates the last results directory """


class DirectoryManagerPlugin:
    name = "directory_manager"

    def __init__(self, config: Optional['Config'] = None):
        from sel4.conf import settings
        self.config = config
        self.paths = dict(settings.PROJECT_PATHS)

    def pytest_configure(self, config: 'Config') -> None:
        if self.config is None:
            self.config = config

    @pytest.hookimpl
    def pytest_archive_results(self) -> Optional[pathlib.Path]:
        import tempfile

        logger_setup = logger.bind(task="setup".rjust(10, ' '))
        source_parent = pathlib.Path(tempfile.gettempdir())
        # -- is there a folder in tmp folder?
        yyyy = date.today().year
        sub_folders = list(source_parent.glob(f'{yyyy}*_[0-9]*'))
        sub_folders.sort(key=os.path.getmtime, reverse=True)
        if len(sub_folders) == 0:
            logger_setup.debug("No last results folder found for archiving ...")
        if len(sub_folders) > 0:
            logger_setup.debug("Found {} sub-folders; archiving....", len(sub_folders))
            from threading import Thread
            arch = self.config.getoption("archive_results", False)
            arch_path = self.paths.get("ARCHIVES")
            mkdir_p(arch_path)
            thread = Thread(target=archive_last_results, args=(sub_folders, arch_path, arch, ))
            thread.daemon = True
            thread.start()
            thread.join()
            return arch_path
        return None

    @pytest.hookimpl
    def pytest_create_results_directory(self):
        with logger.contextualize(task="setup".rjust(10, ' ')):
            logger.debug("Creating project folders if required")
            last_exec = self.paths.get("LAST_EXECUTION")
            if last_exec.exists():
                logger.debug('removing "LAST_EXECUTION" folder')
                rm_rf(last_exec)

            counter = 0
            for folder_name, path in self.paths.items():
                if not path.exists():
                    counter += 1
                    logger.debug('Attempt to create folder\n\t{}:{}', folder_name, path)
                    mkdir_p(path)

            logger.debug("Created {} directories for kiru project", counter)


########################################################################################################################
# FUNCTIONS
########################################################################################################################


def archive_last_results(directories: List[pathlib.Path], arch_folder: pathlib.Path, archive=False) -> bool:
    import shutil

    # -- should be archive?
    if archive:
        source_dir = directories[0]
        new_name = source_dir.name
        dst = arch_folder.joinpath(new_name)
        shutil.move(source_dir, dst)
        from sel4.utils.fileutils import wait_folder_to_be_deleted
        wait_folder_to_be_deleted(source_dir)

    for folder in directories:
        from _pytest.pathlib import rm_rf
        rm_rf(folder)
    return True
