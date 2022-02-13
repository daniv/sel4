########################################################################################################################
# FUNCTIONS
########################################################################################################################
import sys

__all__ = ["colorize_option_group"]

from loguru import logger


def setup_framework():
    """ Set up the testing framework """
    from sel4.conf import settings
    import pathlib

    paths = settings.PROJECT_PATHS

    def _create_last_result_backup():
        src: pathlib.Path = dict(paths).get("LAST_EXECUTION")
        if src.exists():
            import tempfile
            import shutil
            from datetime import datetime
            folder_name = datetime.fromtimestamp(int(src.stat().st_mtime)).strftime("%Y%m%d_%H%M%S")
            dst = pathlib.Path(tempfile.gettempdir()).joinpath(folder_name)
            shutil.move(src, dst)

    def _create_new_execution_folder():
        from sel4.utils.fileutils import mkdir_p
        for name, path in paths:
            if isinstance(path, pathlib.Path):
                logger.debug("Creating directory {}", str(path))
                mkdir_p(path)

    # -- backup last result
    _create_last_result_backup()
    # -- build the execution output folders.
    _create_new_execution_folder()


def colorize_option_group(group_name: str) -> str:
    import colorama
    c1 = ""
    c2 = ""
    cr = ""
    if "linux" not in sys.platform:
        # -- This will be seen when typing "pytest --help" on the command line.
        colorama.init(autoreset=True)
        c1 = colorama.Fore.LIGHTCYAN_EX
        c2 = colorama.Fore.MAGENTA
        cr = colorama.Style.RESET_ALL
    # -- kiru group configuration option
    s_str = group_name.replace(group_name, c1 + group_name + cr)
    return s_str + cr + " " + c2 + "command-line options for pytest" + cr


setup_framework()