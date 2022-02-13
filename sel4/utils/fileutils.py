import os
import pathlib
from typing import Generator, Optional, TYPE_CHECKING

from sel4.utils.retries import retry


__all__ = ["mkdir_p", "wait_folder_to_be_deleted", "iter_find_files"]


if TYPE_CHECKING:
    from sel4.utils.typeutils import ListStr


def mkdir_p(path: pathlib.Path) -> None:
    """
    Create a new directory at this given path.
    If mode is given, it is combined with the process’ umask value to determine the file mode and access flags.

    Any missing parents of this path are created as needed;
    they are created with the default permissions without taking mode into account

    ``FileExistsError`` exceptions will be ignored (same behavior as the POSIX mkdir -p command),
    but only if the last path component is not an existing non-directory file

    :param path: The path to create
    """
    path.mkdir(exist_ok=True, parents=True)


@retry(FileExistsError, timeout_ms=10_000, delay=2, backoff=1.5, jitter=1)
def wait_folder_to_be_deleted(folder: pathlib.Path):
    if folder.exists():
        raise FileExistsError(f"The file {str(folder)} exists")
    return True


def iter_find_files(
        directory: pathlib.Path,
        patterns: 'ListStr',
        ignored: Optional['ListStr'] = None,
        include_dirs: bool = False
) -> Generator[pathlib.Path, None, None]:
    """
    Returns a generator that yields file paths under a *directory* matching *patterns*
    using `glob`_ syntax (e.g., ``*.txt``). Also supports *ignored* patterns.

    :param directory: Path that serves as the root of the search. Yielded paths will include this as a prefix.
    :param patterns:  A single pattern or list of glob-formatted patterns to find under *directory*.
    :param ignored: A single pattern or list of glob-formatted patterns to ignore default is ``None``.
    :param include_dirs: Whether to include directories that match patterns, as well. Defaults to ``False``.
    :type include_dirs:
    :return: a generator that yields file paths under a *directory* matching *patterns*

     For example, finding Python files in the current directory:
     >>> curr_dir = pathlib.Path(__file__).parents[0]
     >>> filenames = sorted(iter_find_files(curr_dir, '*.py'))

     Or, Python files while ignoring emacs lockfiles:

    >>> filenames = iter_find_files(curr_dir, '*.py', ignored='.#*')

    .. _glob: https://en.wikipedia.org/wiki/Glob_%28programming%29
    """
    import re
    import fnmatch
    basestring = (str, bytes)
    if isinstance(patterns, basestring):
        patterns = [patterns]

    pats_re = re.compile('|'.join([fnmatch.translate(p) for p in patterns]))

    if not ignored:
        ignored = []
    elif isinstance(ignored, basestring):
        ignored = [ignored]
    ign_re = re.compile('|'.join([fnmatch.translate(p) for p in ignored]))

    for root, dirs, files in os.walk(str(directory)):
        if include_dirs:
            for basename in dirs:
                if pats_re.match(basename):
                    if ignored and ign_re.match(basename):
                        continue
                    filename = os.path.join(root, basename)
                    yield pathlib.Path(filename)

        for basename in files:
            if pats_re.match(basename):
                if ignored and ign_re.match(basename):
                    continue
                filename = os.path.join(root, basename)
                yield pathlib.Path(filename)
    return
