import os
import pathlib

from .utils.envutils import env

if env("PYTHONPATH", str, None):
    def _add_to_python_path():
        root_path = str(pathlib.Path(__file__).parent.parent)
        if 'PROJECT_ROOT' not in os.environ:
            os.environ.setdefault('PROJECT_ROOT', root_path)
        sel4_path = str(pathlib.Path(__file__).parent)
        if sel4_path not in os.environ['PYTHONPATH']:
            os.environ["PYTHONPATH"] = f'{root_path}:{sel4_path}:' + os.environ['PYTHONPATH']


    _add_to_python_path()
else:
    import sys

    def _create_python_path():
        root_path = str(pathlib.Path(__file__).parent.parent)
        sel4_path = str(pathlib.Path(__file__).parent)
        os.environ.setdefault('PROJECT_ROOT', root_path)
        os.environ.setdefault('PYTHONPATH', f'{root_path}:{sel4_path}:')
        sys.path.append(str(root_path))
        sys.path.append(str(sel4_path))

    _create_python_path()

from rich import get_console, reconfigure
from rich.console import Console
from rich.traceback import install
from sel4.contrib.pydantic.validators import register_validators
from .utils.log import setup_stderr_handler, setup_bootstrap_logger

# print_rich_256_color_names()

reconfigure(force_terminal=True, color_system="256")
# -- installing the rich traceback
error_console = Console(force_terminal=True, color_system="256", stderr=True)
install(show_locals=True, width=get_console().width, console=error_console)
# -- registering arbitrary validators
register_validators()

# -- initializing logging framework
setup_stderr_handler(error_console)
setup_bootstrap_logger()
