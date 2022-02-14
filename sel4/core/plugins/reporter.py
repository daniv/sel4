import pathlib
from abc import ABC
from typing import TYPE_CHECKING, Any, List, Optional, Tuple

from _pytest.config import Config
from loguru import logger
from pydantic import BaseModel, Field, FilePath
from pytest import Mark, hookimpl, hookspec

from sel4.conf import settings
from sel4.utils.typeutils import DictStrAny, NoneStr, OptionalInt

if TYPE_CHECKING:
    from pytest import (
        CallInfo,
        CollectReport,
        ExitCode,
        Item,
        PytestPluginManager,
        Session,
        TestReport,
    )


class ItemMark(BaseModel):
    name: str
    args: Optional[Tuple] = None
    kwargs: Optional[DictStrAny] = None

class TestItem(BaseModel):
    fspath: FilePath
    path: FilePath
    location: Tuple[str, int, str]
    name: str
    nodeid: str
    originalname: str
    markers: List[ItemMark]
    user_properties = List[Any]

    class Config:
        arbitrary_types_allowed = True


class CollectedItem(BaseModel):
    name: str
    # original_name: str
    node_id: str
    type: str
    display_id: str
    log_path: pathlib.Path
    file_path: NoneStr = None  #  FilePath
    line_no: OptionalInt = None
    own_markers: List[Mark] = Field(default_factory=list)
    selected: bool = True

    class Config:
        arbitrary_types_allowed = True


class SessionResults(BaseModel):
    passed: int = Field(default=0, description="Summary of test passed")
    xfailed: int = Field(default=0, description="Total of test xfailed")
    failed: int = Field(default=0, description="Total of test failed")
    skipped: int = Field(default=0, description="Total of test skipped")
    xpassed: int = Field(default=0, description="Total of test xpassed")
    errors: int = Field(default=0, description="Total of errors")
    rerun: OptionalInt = Field(
        default=None, description="Total of reruns if rerun failures plugin present"
    )


class ReporterHooks:
    def pytest_report_modifyreport(self, json_report):
        """Called after building JSON report and before saving it.
        Plugins can use this hook to modify the report before it's saved.
        """

    @hookspec(firstresult=True)
    def pytest_report_runtest_stage(self, report: "TestReport"):
        """Return a dict used as the JSON representation of `report` (the
        `_pytest.runner.TestReport` of the current test stage).
        Called from `pytest_runtest_logreport`. Plugins can use this hook to
        overwrite how the result of a test stage run gets turned into JSON.
        """

    def pytest_report_runtest_metadata(self, item: "Item", call: "CallInfo[None]"):
        """Return a dict which will be added to the current test item's JSON
        metadata.
        Called from `pytest_runtest_makereport`. Plugins can use this hook to
        add metadata based on the current test run.
        """


class PyTestReporterBase(ABC):
    name = "pytest-reporter"

    def __init__(self, config: "Config"):
        self._config = config
        self.paths = dict(settings.PROJECT_PATHS)
        self._passed: bool = False
        self._skipped: bool = False
        self._failed: bool = False
        self._outcome: str = ""


    @staticmethod
    def pytest_addhooks(pluginmanager: "PytestPluginManager"):
        pluginmanager.add_hookspecs(ReporterHooks)

    def pytest_configure(self, config: "Config") -> None:
        if self._config is None:
            self._config = config

    @hookimpl(hookwrapper=True)
    def pytest_runtest_protocol(self, item: 'Item', nextitem: Optional["Item"]) -> Optional[object]:
        """
        Perform the runtest protocol for a single test item.

        :param item:  Test item for which the runtest protocol is performed.
        :param nextitem: The scheduled-to-be-next test item (None if no further test item is scheduled).
        """
        yield

    @hookimpl(hookwrapper=True)
    def pytest_runtest_setup(self, item: "Item") -> None:
        """
        Called to perform the setup phase for a test item.

        :param item: Test item for which the runtest protocol is performed.
        """
        yield

    @hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item: "Item") -> None:
        """
        Called to run the test for test item (the call phase).

        :param item: Test item for which the runtest protocol is performed.
        """
        yield

    @hookimpl(hookwrapper=True)
    def pytest_runtest_teardown(self, item: "Item", nextitem: Optional["Item"]) -> None:
        """
        Called to perform the teardown phase for a test item.

        :param item:  Test item for which the runtest protocol is performed.
        :param nextitem: The scheduled-to-be-next test item (None if no further test item is scheduled).
        """
        yield

    @hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item: "Item", call: "CallInfo[None]") -> Optional["TestReport"]:
        """
        Called to create a _pytest.reports.TestReport for each of the setup,
        call and teardown runtest phases of a test item.

        :param item:
        :param call:
        :return:
        """
        report = (yield).get_result()
        if report.when == "call":
            self._skipped = report.skipped
            self._passed = report.passed
            self._failed = report.failed
            self._outcome = report.outcome



class PyTestReporterWorker(PyTestReporterBase):
    pass


class PyTestReporter(PyTestReporterBase):
    def __init__(self, config: "Config"):
        super().__init__(config)
        # noinspection PyProtectedMember
        from loguru._logger import start_time

        self._started = start_time
        self._started_session = None
        self._collectors = []

        self.session_results = SessionResults()
        has_rerun = config.pluginmanager.hasplugin("rerunfailures")
        if has_rerun:
            self.session_results.rerun = 0

    def pytest_sessionstart(self, session: "Session") -> None:
        """
        Called after the Session object has been created and before performing collection and
        entering the run test loop.

        :param session: The pytest session object.
        """
        logger.debug("Invoked session start")
        from loguru._datetime import aware_now
        self._started_session = aware_now()

    def pytest_collectreport(self, report: "CollectReport"):
        """
        Collector finished collecting.

        :param report: The collection report
        """
        if report.nodeid:
            pass
            for item in report.result:
                print(item.__class__.__name__)
            #     collected_item = CollectedItem(
            #         node_id=item.nodeid,
            #         name=item.name,
            #         # original_name=item.originalname,
            #         type=item.__class__.__name__,
            #         display_id="",
            #         log_path=self.paths.get("LOGS").joinpath("eee"),
            #         line_no=item.location[1] if hasattr(item, "location") else None,
            #         file_path=item.location[2] if hasattr(item, "location") else None,
            #         own_markers=item.own_markers,
            #     )
            #     setattr(item, "_collected_item", collected_item)
            #     self._collectors.append(collected_item)
            # logger.info("Collected {} test items", len(self._collectors))

    def pytest_deselected(self, items: List["Item"]):
        """
        Called for deselected test items, e.g. by keyword.

        :param items: The de
        :return:
        """
        for item in items:
            try:
                ci = getattr(item, "_collected_item")
                ci.selected = False
            except AttributeError:
                continue

    @hookimpl(hookwrapper=True)
    def pytest_collection_modifyitems(self, session: "Session", config: "Config", items: List["Item"]) -> None:
        """
        Called after collection has been performed. May filter or re-order the items in-place.

        :param session: The pytest session object.
        :param config:  The pytest config object.
        :param items: List of item objects.
        """
        yield
        # for item in items:
        #     del item._json_collectitem

    def pytest_runtest_logreport(self, report: "TestReport"):
        """
        Process the _pytest.reports.TestReport produced for each of the setup,
        call and teardown runtest phases of an item.

        :param report: The test report object
        :return:
        """
        if getattr(report, "when", None) == "call":
            if report.failed:
                if hasattr(report, "wasxfail"):
                    self.session_results.xpassed += 1
                else:
                    self.session_results.failed += 1
            elif report.passed:
                if hasattr(report, "wasxfail"):
                    self.session_results.xpassed += 1
                else:
                    self.session_results.passed += 1
            elif self._skipped:
                if hasattr(report, "wasxfail"):
                    self.session_results.xfailed += 1
                else:
                    self.session_results.skipped += 1
        else:
            if report.failed:
                self.session_results.errors += 1
        node_id = report.nodeid
        pass

    @hookimpl(trylast=True)
    def pytest_report_runtest_stage(self, report: "TestReport"):
        pass

    @hookimpl(tryfirst=True)
    def pytest_sessionfinish(self, session: "Session", exitstatus: "ExitCode") -> None:
        """
        Called after whole test run finished, right before returning the exit status to the system.

        :param session: The pytest session object.
        :param exitstatus: The status which pytest will return to the system.
        """
        pass

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
