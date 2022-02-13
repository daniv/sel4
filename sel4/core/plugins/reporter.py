import pathlib

from _pytest.config import Config
from pydantic import BaseModel, Field

from sel4.utils.typeutils import OptionalInt


class CollectedItem(BaseModel):
    node_id: str
    display_id: str
    log_path: pathlib.Path


class SessionResults(BaseModel):
    passed: int = Field(default=0, description="Summary of test passed")
    xfailed: int = Field(default=0, description="Total of test xfailed")
    failed: int = Field(default=0, description="Total of test failed")
    skipped: int = Field(default=0, description="Total of test skipped")
    xpassed: int = Field(default=0, description="Total of test xpassed")
    errors: int = Field(default=0, description="Total of errors")
    rerun: OptionalInt = Field(default=None, description="Total of reruns if rerun failures plugin present")


class HtmlReporter:
    name = "html-reporter"

    def __init__(self, config: "Config"):
        self.config = config
        self.session_results = SessionResults()
        has_rerun = config.pluginmanager.hasplugin("rerunfailures")
        if has_rerun:
            self.session_results.rerun = 0

    def append_passed(self, report):
        if report.when == "call":
            if hasattr(report, "wasxfail"):
                self.session_results.xpassed += 1
            else:
                self.session_results.passed += 1

    def append_failed(self, report):
        if getattr(report, "when", None) == "call":
            if hasattr(report, "wasxfail"):
                self.session_results.xpassed += 1
            else:
                self.session_results.failed += 1
        else:
            self.session_results.errors += 1

    def append_rerun(self, report):
        self.session_results.rerun += 1

    def append_skipped(self, report):
        self.session_results.rerun += 1