import sys

from .base import *  # noqa F401

########################################################################################################################
# CORE
########################################################################################################################

EXECUTION_ROOT = PROJECT_ROOT.joinpath("out").joinpath("local")  # noqa F405
RESOURCES_FOLDER = PROJECT_ROOT.joinpath("resources/local")  # noqa F405
PROJECT_PATHS = [
    ("ARCHIVES", EXECUTION_ROOT.joinpath("archives")),
    ("LAST_EXECUTION", EXECUTION_ROOT.joinpath("pytest_exec")),
    ("LOGS", EXECUTION_ROOT.joinpath("pytest_exec/logs")),
    ("SCREENSHOTS", EXECUTION_ROOT.joinpath("pytest_exec/reports/screenshots")),
    ("DOWNLOADS", EXECUTION_ROOT.joinpath("pytest_exec/downloads")),
    ("REPORTS", EXECUTION_ROOT.joinpath("pytest_exec/reports")),
    ("REQUESTS", EXECUTION_ROOT.joinpath("pytest_exec/reports/requests")),
    ("ERRORS", EXECUTION_ROOT.joinpath("pytest_exec/reports/errors")),
    ("PAGE_SOURCES", EXECUTION_ROOT.joinpath("pytest_exec/reports/page_sources")),
]
HOME_URL = ""

########################################################################################################################
# LOCAL SETTINGS - SECRETS
########################################################################################################################
try:
    from kiru.settings.local_settings import *  # noqa: F401
except ImportError:
    pass
