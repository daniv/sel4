import os
import sys
from ipaddress import IPv4Address, IPv6Address
from typing import Optional

from pydantic import BaseModel
from pytest import Config

from sel4.core import constants
from sel4.utils.typeutils import DictStrAny


class Metadata(BaseModel):
    env: DictStrAny
    git_changeset: int
    environment: constants.Environments
    platform_name: str
    platform_arch: str
    ip_address: IPv6Address | IPv4Address
    username: str
    packages: DictStrAny
    plugins: Optional[DictStrAny] = None
    python_version: str


def collect_metadata(config: Config, print_metadata=True) -> Metadata:
    envs = {
        "PYTHONPATH": os.environ.get("PYTHONPATH"),
        "PROJECT_ROOT": os.environ.get("PROJECT_ROOT"),
        "SEL4_SETTINGS_MODULE": os.environ.get("SEL4_SETTINGS_MODULE"),
        "COMPUTER_NAME": os.environ.get("COMPUTERNAME", "N/A"),
        "VIRTUAL_ENV": os.environ.get("VIRTUAL_ENV", "N/A"),
    }
    import platform

    import pkg_resources

    arch, os_arch = platform.architecture()
    pluggy_version = pkg_resources.get_distribution("pluggy").version
    httpx_version = pkg_resources.get_distribution("httpx").version
    pytest_version = pkg_resources.get_distribution("pytest").version
    selenium_version = pkg_resources.get_distribution("selenium").version
    py_version = pkg_resources.get_distribution("py").version

    from sel4.utils.envutils import env
    from sel4.utils.gitutils import get_git_changeset
    from sel4.utils.netutils import current_ip_address

    metadata = Metadata(
        env=envs,
        git_changeset=get_git_changeset(),
        environment=config.getini("environment"),
        platform_name=sys.platform,
        platform_arch=arch,
        ip_address=current_ip_address(),
        username=env("USERNAME", str, "N/A"),
        python_version=platform.python_version(),
        packages={
            "pytest": pytest_version,
            "py": py_version,
            "pluggy": pluggy_version,
            "selenium": selenium_version,
            "httpx": httpx_version,
        },
    )
    if print_metadata:
        print_intro_table(metadata)
    return metadata


def print_intro_table(metadata: Metadata):
    from rich import box
    from rich.table import Table

    _table = Table(
        title="sel4 automation framework",
        caption="Versions used by the framework",
        min_width=80,
        box=box.ROUNDED,
        style="pale_green3",
        title_justify="center",
        caption_justify="center",
        highlight=True,
        show_header=True,
    )
    _table.add_column("Item")
    _table.add_column("Value")
    _table.add_row("git change-set", str(metadata.git_changeset))
    _table.add_row("username", metadata.username)
    _table.add_row("platform", metadata.platform_name)
    _table.add_row("ip address", str(metadata.ip_address))
    _table.add_row("environment", metadata.environment)
    _table.add_row("python version", metadata.python_version)
    for k, v in metadata.packages.items():
        _table.add_row(f"{k} version", v)

    from rich import get_console

    get_console().print(_table)
