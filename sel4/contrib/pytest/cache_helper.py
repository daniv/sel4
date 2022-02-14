import pathlib
from typing import TYPE_CHECKING, final

from loguru import logger

if TYPE_CHECKING:
    from _pytest.cacheprovider import Cache


@final
class PytestCache:
    # directory under cache-dir for directories created by "makedir"
    _CACHE_PREFIX_DIRS = ""

    # directory under cache-dir for values created by "set"
    _CACHE_PREFIX_VALUES = ""

    def __init__(self, pytest_cache: "Cache"):
        self._pytest_cache = pytest_cache
        self._CACHE_PREFIX_DIRS = getattr(pytest_cache, "_CACHE_PREFIX_DIRS")
        self._CACHE_PREFIX_VALUES = getattr(pytest_cache, "_CACHE_PREFIX_VALUES")

    def delete_cache_older_than_x_days(self, cache_path: pathlib.Path, days: int):
        from datetime import datetime

        setup_logger = logger.bind(task="setup".rjust(10, " "))

        from dateutil.relativedelta import relativedelta

        delta = datetime.now() + relativedelta(days=days)
        time_to_shift = datetime.timestamp(delta)
        for prefix in (self._CACHE_PREFIX_DIRS, self._CACHE_PREFIX_VALUES):
            setup_logger.debug(
                "Scanning cache directory '{prefix}' for files older than: {days} days",
                prefix=prefix,
                days=abs(days),
            )
            curr_dir = cache_path / prefix
            from sel4.utils.fileutils import iter_find_files

            files = list(
                iter_find_files(
                    curr_dir, "*", ignored=["stepwise", "nodeids", "lastfailed"]
                )
            )
            for file in files:
                item_time = file.stat().st_mtime
                if file.is_file():
                    if item_time < time_to_shift:
                        setup_logger.debug("Deleting cache file: {}", str(file.name))
                        file.unlink(missing_ok=False)
