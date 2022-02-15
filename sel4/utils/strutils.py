"""
source : https://github.com/mahmoud/boltons/blob/master/boltons/strutils.py
"""
import os
import re
import threading
import uuid
import socket
import platform
from typing import Any, Dict, List, Mapping, Text, Tuple, Union

__all__ = [
    "import_string", "multi_replace", "keep_alphanumerics", "parse_bool",
    "host_tag", "thread_tag", "get_uuid4", "platform_label"
]


def import_string(dotted_path: str) -> Any:
    """
    Stolen approximately from django. Import a dotted module path and return the attribute/class designated by the
    last name in the path. Raise ImportError if the import fails.
    """
    from importlib import import_module

    try:
        module_path, class_name = dotted_path.strip(" ").rsplit(".", 1)
    except ValueError as e:
        raise ImportError(f'"{dotted_path}" doesn\'t look like a module path') from e

    module = import_module(module_path)
    try:
        return getattr(module, class_name)
    except AttributeError as e:
        raise ImportError(f'Module "{module_path}" does not define a "{class_name}" attribute') from e


class MultiReplace:
    """
    MultiReplace is a tool for doing multiple find/replace actions in one pass.

    Given a mapping of values to be replaced it allows for all of the matching
    values to be replaced in a single pass which can save a lot of performance
    on very large strings. In addition to simple replace, it also allows for
    replacing based on regular expressions.

    """

    def __init__(self, sub_map, **kwargs):
        """Multi replce strings.

        :param sub_map:
        :type sub_map:
        :param kwargs:
        :type kwargs:

        Keyword Arguments:
        :type regex: bool
        :param regex: Treat search keys as regular expressions [Default: False]
        :type flags: int
        :param flags: flags to pass to the regex engine during compile

        Dictionary usage:
        >>> from sel4.utils import strutils
        >>> s = strutils.MultiReplace({
        >>>         'foo': 'zoo',
        >>>         'cat': 'hat',
        >>>         'bat': 'kraken'
        >>>     })
        >>> new = s.sub('The foo bar cat ate a bat')
        >>> new == 'The zoo bar hat ate a kraken'

        Iterable Usage::
        >>> from sel4.utils import strutils
        >>> s = strutils.MultiReplace([
        >>>         ('foo', 'zoo'),
        >>>         ('cat', 'hat'),
        >>>         ('bat', 'kraken')
        >>>     ])
        >>> new = s.sub('The foo bar cat ate a bat')
        >>> new == 'The zoo bar hat ate a kraken'
        """
        options = {
            "regex": False,
            "flags": 0,
        }
        options.update(kwargs)
        self.group_map = {}
        regex_values = []

        if isinstance(sub_map, Mapping):
            sub_map = sub_map.items()

        for idx, vals in enumerate(sub_map):
            group_name = "group{0}".format(idx)
            if isinstance(vals[0], (str, bytes)):
                # If we're not treating input strings like a regex, escape it
                if not options["regex"]:
                    exp = re.escape(vals[0])
                else:
                    exp = vals[0]
            else:
                exp = vals[0].pattern

            regex_values.append("(?P<{0}>{1})".format(group_name, exp))
            self.group_map[group_name] = vals[1]

        self.combined_pattern = re.compile("|".join(regex_values), flags=options["flags"])

    def _get_value(self, match):
        """Given a match object find replacement value."""
        group_dict = match.groupdict()
        key = [x for x in group_dict if group_dict[x]][0]
        return self.group_map[key]

    def sub(self, text):
        """
        Run substitutions on the input text.
        Given an input string, run all substitutions given in the
        constructor.
        """
        return self.combined_pattern.sub(self._get_value, text)


def multi_replace(text: Text, sub_map: Union[List[Tuple[Text, Text]], Dict[Text, Text]], **kwargs):
    """
    Shortcut function to invoke MultiReplace in a single call.
    """
    m = MultiReplace(sub_map, **kwargs)
    return m.sub(text)


def keep_alphanumerics(text: Text, flag: int) -> Text:
    if flag == re.UNICODE:
        return re.sub(r"[\W_]+", "", text, flags=re.UNICODE)
    if flag == re.LOCALE:
        return re.sub(r"[\W_]+", "", text, flags=re.LOCALE)
    raise ValueError(f"flag {str(flag)} is not implemented in this function")


def strtobool(val: str) -> int:
    """Convert a string representation of truth to true (1) or false (0).

    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return 1
    elif val in ("n", "no", "f", "false", "off", "0"):
        return 0
    else:
        raise ValueError("invalid truth value %r" % (val,))


def parse_bool(text: str) -> bool:
    return bool(strtobool(text))


def get_uuid4():
    return str(uuid.uuid4())


def platform_label():
    major_version, _, __ = platform.python_version_tuple()
    implementation = platform.python_implementation()
    return f'{implementation.lower()}{major_version}'


def thread_tag():
    return '{0}-{1}'.format(os.getpid(), threading.current_thread().name)


def host_tag():
    return socket.gethostname()