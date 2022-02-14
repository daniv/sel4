import pathlib
import shutil
from collections import defaultdict
from typing import List

from loguru import logger
from pydantic import BaseModel, Field

from sel4.conf import settings
from sel4.utils.fileutils import mkdir_p
from sel4.utils.typeutils import DictStrAny


class TestId(BaseModel):
    results: DictStrAny = Field(default_factory=lambda: defaultdict(lambda: None))
    result: str
    duration: float = 0.0
    display_id: str
    log_path: pathlib.Path


class Dashboard(BaseModel):
    items_count: int = 0
    tests: List[TestId] = Field(default_factory=list)


def create_dashboard():
    paths = dict(settings.PROJECT_PATHS)
    exec_folder = paths.get("LAST_EXECUTION")
    assets_folder: pathlib.Path = exec_folder.joinpath("dashboard")
    mkdir_p(assets_folder)

    dashboard_logger = logger.bind(task="dashboard".rjust(10, " "))
    file: pathlib.Path = settings.RESOURCES_ROOT.joinpath("dashboard", "pytest_style.css")
    pytest_style_css: pathlib.Path = shutil.copy(file, assets_folder)
    dashboard_logger.info("Copied file pytest_style.css to {}", pytest_style_css)
    file: pathlib.Path = settings.RESOURCES_ROOT.joinpath("dashboard", "live.js")
    live_js: pathlib.Path = shutil.copy(file, assets_folder)
    dashboard_logger.info("Copied file live.js to {}", live_js)
