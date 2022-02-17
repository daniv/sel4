import os
import re
import sys
from typing import TYPE_CHECKING, List

import pydantic
from loguru import logger

from .. import constants

if TYPE_CHECKING:
    from _pytest.config import Config
    from _pytest.config.argparsing import Parser


class EnvironmentModel(pydantic.BaseModel):
    environment: constants.Environments = pydantic.Field(
        default=None, description="The working environment"
    )


def pytest_load_initial_conftests(
    early_config: "Config", parser: "Parser", args: List[str]
) -> None:
    """Called to implement the loading of initial conftest files ahead of command line option parsing.

    .note::
        This hook will not be called for ``conftest.py`` files, only for setuptools plugins.

    :param early_config: The pytest config object.
    :param args: Arguments passed on the command line.
    :param parser: To add command line options.
    """
    os.environ.setdefault("PROJECT_ROOT", str(early_config.rootdir))
    patched = logger.patch(lambda x: x["extra"].update(task="bootstrap".rjust(10, " ")))
    patched.trace(
        "Setting environment 'PROJECT_ROOT' to {rootdir}",
        rootdir=str(early_config.rootdir),
    )

    # search settings in environment
    from sel4.utils.envutils import env

    settings_module = env("SEL4_SETTINGS_MODULE", str, None)
    if settings_module is None:
        # no environment variable found, searching via sys.argv
        pattern = re.compile(r"--env=\w+")
        expression = next(filter(lambda x: pattern.match(x), args), None)
        if expression is None:
            settings_file = f"sel4.settings.{constants.Environments.LOCAL}"
            os.environ.setdefault("SEL4_SETTINGS_MODULE", settings_file)
            parser.addini(
                "environment",
                type="string",
                default=constants.Environments.LOCAL,
                help="The sel4 working environment",
            )
        else:
            index = args.index(expression)
            env = args.pop(index)
            env_value = env.split("=")[1]
            settings_file = constants.Environments.settings().get(
                constants.Environments(env_value)
            )
            os.environ.setdefault("SEL4_SETTINGS_MODULE", settings_file)
            EnvironmentModel(environment=env_value)
            parser.addini(
                "environment",
                type="string",
                default=env_value,
                help="The sel4 working environment",
            )

    if "--strict-markers" not in args:
        args.append("--strict-markers")
    if "--color" not in args:
        args[:] = ["--color", "yes"] + args
    if "--code-highlight" not in args:
        args[:] = ["--code-highlight", "yes"] + args
    os.environ.setdefault("PY_COLORS", "1")
    args = sys.argv
    if "-h" in sys.argv:
        early_config.pluginmanager.import_plugin("sel4.core.plugins.webdriver")
    if "--chrome" in args or "--edge" in args or "--safari" in args:
        patched.info(
            "Detected browser configuration session. "
            'setting environ "PYTEST_PLUGINS" to register <sel4.core.plugins.webdriver>'
        )
        os.environ.setdefault("PYTEST_PLUGINS", "sel4.core.plugins.webdriver")
