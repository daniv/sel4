import sys
from typing import TYPE_CHECKING

from loguru import logger
from rich.console import Console
from rich.logging import RichHandler

from sel4 import env

if TYPE_CHECKING:
    from loguru import Logger


def setup_stderr_handler(error_console: Console) -> int:
    rich_handler = RichHandler(
        level="ERROR",
        console=error_console,
        show_path=True,
        enable_link_path=True,
        markup=True,
        tracebacks_width=error_console.width,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
    )
    return logger.add(
        sink=rich_handler,
        level=rich_handler.level,
        backtrace=False,
        colorize=False,
        diagnose=False,
        catch=True,
    )


def setup_bootstrap_logger() -> "Logger":
    console = Console(file=sys.stdout, force_terminal=True, color_system="truecolor")
    level = "DEBUG" if "pydevd" in sys.modules else "INFO"
    level = env("LOG_LEVEL", str, level)

    rich_handler = RichHandler(
        level=level,
        console=console,
        show_path=True,
        enable_link_path=True,
        markup=True,
        rich_tracebacks=False,
        log_time_format="%X",
    )
    logger.configure(
        handlers=[
            {
                "sink": rich_handler,
                "format": "[grey53]{extra[task]}[/]: [slate_blue1]{function}[/] -> {message}",
                "level": rich_handler.level,
                "backtrace": "False",
            }
        ],
        extra={"task": "config".rjust(10, " ")},
    )
    # bootstrap = logger.bind(task="bootstrap".rjust(10, ' '))
    bootstrap = logger.bind(task="bootstrap".rjust(10, " "))
    bootstrap.info("Logging was properly configured.")
    return bootstrap


def setup_session_logger():
    console = Console(
        file=sys.stdout,
        force_terminal=True,
        color_system="truecolor",
    )
    level = "DEBUG" if "pydevd" in sys.modules else "INFO"
    rich_handler = RichHandler(
        level=level,
        console=console,
        show_path=True,
        enable_link_path=True,
        markup=True,
        rich_tracebacks=True,
        log_time_format="%X",
    )
    logger.remove(2)
    logger.add(
        sink=rich_handler,
        level=level,
        format="[slate_blue1]{function}[/] -> {message}",
        backtrace=True,
        diagnose=True,
        catch=True,
    )
