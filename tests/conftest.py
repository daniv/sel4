""" Parametrizing conditional raising:

Different options for test IDs:
Indirect parametrization: https://docs.pytest.org/en/latest/example/parametrize.html
Markers: https://docs.pytest.org/en/6.2.x/example/markers.html
writing hooks: https://docs.pytest.org/en/latest/how-to/writing_hook_functions.html
pytest hooks: writing
stash: https://docs.pytest.org/en/latest/reference/reference.html#pytest.Stash


Initialization Hooks
====================
- pytest_addoption: Register argparse-style options and ini-style config values,
                    called once at the beginning of a test run
- pytest_addhooks:  Called at plugin registration time to allow adding new hooks via a call to
                    `pluginmanager.add_hookspecs(module_or_class, prefix)`
- pytest_configure: Allow plugins and conftest files to perform initial configuration.
- pytest_unconfigure: Called before test process is exited.
- pytest_sessionstart: Called after the Session object has been created and before
                       performing collection and entering the run test loop.
- pytest_sessionfinish: Called after whole test run finished, right before returning the exit status to the system.
- pytest_plugin_registered: A new pytest plugin got registered.

Collection Hooks
================
- pytest_collection: Perform the collection phase for the given session.
    * pytest_collectstart:
    * pytest_make_collect_report:
    * pytest_exception_interact: if an interactive exception occurred
    * pytest_itemcollected:
    * pytest_collectreport:
    * pytest_collection_modifyitems:
    * pytest_collection_finish:
- pytest_ignore_collect: Return True to prevent considering this path for collection
- pytest_collect_file: Create a Collector for the given path, or None if not relevant
- pytest_pycollect_makemodule: Return a Module collector or None for the given path.
- pytest_pycollect_makeitem: Return a custom item/collector for a Python object in a module, or None.
- pytest_make_parametrize_id: Return a user-friendly string representation of the given val that will be
                              used by @pytest.mark.parametrize calls, or None if the hook doesn’t know about val.
- pytest_generate_tests: Generate (multiple) parametrized calls to a test function
- pytest_collection_modifyitems: Called after collection has been performed.
                                May filter or re-order the items in-place.
- pytest_collection_finish: Called after collection has been performed and modified.

RunTest Hooks
=============
- pytest_runtestloop: Perform the main runtest loop (after collection finished).
- pytest_runtest_protocol: Perform the runtest protocol for a single test item.
    * ---- Setup phase ----
    * pytest_runtest_logstart
    * pytest_runtest_setup
    * pytest_runtest_logreport
    * pytest_exception_interact
    *  ---- Call phase ----
    * pytest_runtest_call
    * pytest_runtest_makereport
    * pytest_runtest_logreport
    * pytest_exception_interact
    * ---- Teardown phase ----
    * pytest_runtest_teardown
    * pytest_runtest_makereport
    * pytest_runtest_logreport
    * pytest_exception_interact
    * pytest_runtest_logfinish
- pytest_runtest_logstart: Called at the start of running the runtest protocol for a single item.
- pytest_runtest_setup: Called at the end of running the runtest protocol for a single item.
- pytest_runtest_logreport: Called to perform the setup phase for a test item.
- pytest_runtest_call: Called to run the test for test item (the call phase).
- pytest_runtest_makereport: Called to create a `_pytest.reports.TestReport` for each of the setup,
- pytest_runtest_teardown: Called to perform the teardown phase for a test item.
- pytest_pyfunc_call: Call underlying test function.

Reporting Hooks
===============
- pytest_collectstart: Collector starts collecting.
- pytest_make_collect_report: Perform `collector.collect()` and return a CollectReport.
- pytest_itemcollected: We just collected a test item.
- pytest_collectreport: Collector finished collecting.
- pytest_deselected: Called for deselected test items, e.g. by keyword.
- pytest_report_header: Return a string or list of strings to be displayed as header info for terminal reporting.
- pytest_report_collectionfinish: Return a string or list of strings to be displayed after
                                  collection has finished successfully
- pytest_report_teststatus: Return result-category, shortletter and verbose word for status reporting.
- pytest_terminal_summary: Add a section to terminal summary reporting.
- pytest_fixture_setup: Perform fixture setup execution.
- pytest_fixture_post_finalizer: Called after fixture teardown, but before the cache is cleared,
                                 so the fixture result `fixturedef.cached_result` is still available (not None)
- pytest_warning_recorded: Process a warning captured by the internal pytest warnings plugin.
- pytest_runtest_logreport: Process the `_pytest.reports.TestReport` produced for each of the setup,
                            call and teardown runtest phases of an item.
- pytest_assertrepr_compare: Return explanation for comparisons in failing assert expressions.
- pytest_assertion_pass: Called whenever an assertion passes.

Debugging Hooks
===============
- pytest_internalerror: Called for internal errors.
- pytest_keyboard_interrupt: Called for keyboard interrupt.
- pytest_exception_interact: Called when an exception was raised which can potentially be interactively handled.
- pytest_enter_pdb: Called upon pdb.set_trace().
"""
import os
import pathlib
import re
import sys
from collections import defaultdict
from typing import TYPE_CHECKING, List, Optional, Sequence, cast

from loguru import logger
from pytest import StashKey, fixture, hookimpl
from rich import get_console

from sel4.contrib.argparse import argtypes
from sel4.core.dashboard import Dashboard, TestId
from sel4.core.exceptions import ImproperlyConfigured
from sel4.core.runtime import runtime_store

pytest_plugins = ["pytester"]


if TYPE_CHECKING:
    from _pytest.config import _PluggyPlugin
    from pytest import Config, Parser, PytestPluginManager


########################################################################################################################
# PYTEST INITIALIZATION HOOK IMPLEMENTATIONS
########################################################################################################################

# region PYTEST INITIALIZATION HOOK IMPLEMENTATIONS


# region pytest_addhooks(pluginmanager)


def pytest_addhooks(pluginmanager: "PytestPluginManager") -> None:
    """Called at plugin registration time to allow adding new hooks via a call to pluginmanager.

    :param pluginmanager: pytest plugin manager.
    """
    pluginmanager.enable_tracing()
    logger.trace("Registering hooks from 'PytestHooks' and 'DirectoryManagerHooks'")
    from sel4.core.plugins.directory_manager import DirectoryManagerHooks

    pluginmanager.add_hookspecs(DirectoryManagerHooks)
    # from core.plugins.hooks import PytestHooks
    # pluginmanager.add_hookspecs(PytestHooks)
    pluginmanager.add_hookcall_monitoring(before=_before_hook, after=_after_hook)

# endregion pytest_addhooks(pluginmanager)

# region pytest_addoption(parser, pluginmanager)


@hookimpl
def pytest_addoption(parser: "Parser", pluginmanager: "PytestPluginManager") -> None:
    """
    Register argparse-style options and ini-style config values, called once at the beginning of a test run.

    :param parser: To add command line options,
                   call parser.addoption(...). To add ini-file values call parser.addini(...)
    :param pluginmanager: pytest plugin manager.

        :see: https://docs.pytest.org/en/6.2.x/_modules/_pytest/main.html

        This plugin adds the following command-line options to pytest:
            --xvfb  (Run tests using the Xvfb virtual display server on Linux OS.)
            --archive-results - Archive test results
            --slow  (Slow down the automation. Faster than using Demo Mode.)
            --timeout-multiplier  (Multiplies the default timeout values.)
            --demo  (Slow down and visually see test actions as they occur.)
            --demo-sleep SECONDS  (Set the wait time after Demo Mode actions.)
            --dashboard  (Enable the Dashboard. Saved at: dashboard.html)
    """
    if "PYTEST_PLUGINS" in os.environ:
        logger.bind(task="setup".rjust(10, " ")).debug(
            '<os.environ "PYTEST_PLUGINS"> was set, loading plugins [consider_env]...'
        )
        pluginmanager.consider_env()

    from tests import colorize_option_group

    s_str = colorize_option_group("Sel4Automation")
    sel4_group = parser.getgroup(name="Sel4Automation", description=s_str)
    ctx_logger = logger.bind(task="setup".rjust(10, " "))
    ctx_logger.debug(
        'adding "Sel4Automation conftest-plugin" command-line options for [bold]pytest[/] ...'
    )

    # region --xvfb
    sel4_group.addoption(
        "--xvfb",
        action="store_true",
        dest="xvfb",
        default=False,
        help="""Using this makes tests run headless using Xvfb
                   instead of the browser's built-in headless mode.
                   When using "--xvfb", the "--headless" option
                   will no longer be enabled by default on Linux.
                   Default: False. (Linux-ONLY!)""",
    )
    # endregion --xvfb

    # region --archive-results, --archive
    sel4_group.addoption(
        "--archive-results",
        "--archive",
        action="store_true",
        dest="archive_results",
        default=False,
        help="Archive old results files instead of deleting them. defaults to %(default)s",
    )
    # endregion --archive-results, --archive

    # region --slow-mode, --slow
    sel4_group.addoption(
        "--slow-mode",
        "--slow",
        action="store_true",
        dest="slow_mode",
        default=False,
        help="""Using this slows down the automation.""",
    )
    # endregion --slow-mode, --slow

    # region --timeout-multiplier
    sel4_group.addoption(
        "--timeout-multiplier",
        action="store",
        dest="timeout_multiplier",
        type=float,
        default=0.0,
        help="""Setting this overrides the default timeout
                by the multiplier when waiting for page elements.
                Unused when tests override the default value.""",
    )
    # endregion --timeout-multiplier

    # region --demo-mode, --demo
    sel4_group.addoption(
        "--demo-mode",
        "--demo",
        action="store_true",
        dest="demo_mode",
        default=False,
        help="""Using this slows down the automation and lets you
                   visually see what the tests are actually doing.""",
    )
    # endregion --demo-mode, --demo

    # region --demo-sleep
    sel4_group.addoption(
        "--demo-sleep",
        action="store",
        dest="demo_sleep",
        metavar="TIME:SECONDS",
        default=1,
        type=argtypes.ConstrainedIntArgType(strict=True, ge=1),
        help="""Setting this overrides the Demo Mode sleep
                   time that happens after browser actions.""",
    )
    # endregion --demo-sleep

    # region --time-limit
    sel4_group.addoption(
        "--time-limit",
        action="store",
        dest="time_limit",
        metavar="SECONDS",
        type=int,
        default=0,
        help="""Use this to set a time limit per test, in seconds.
                   If a test runs beyond the limit, it fails.""",
    )
    # endregion --time-limit

    # region --dashboard
    parser.addoption(
        "--dashboard",
        action="store_true",
        dest="dashboard",
        default=False,
        help="""Using this enables the framework Dashboard.
                   To access the framework Dashboard interface,
                   open the dashboard.html file located in the same
                   folder that the pytest command was run from.""",
    )
    # endregion --dashboard

    sys_argv = sys.argv
    # Dashboard Mode does not support tests using forked subprocesses.
    if "--forked" in sys_argv and "--dashboard" in sys_argv:
        raise ImproperlyConfigured(
            "\n\n  Dashboard Mode does NOT support forked subprocesses!"
            '\n  (*** DO NOT combine "--forked" with "--dashboard"! ***)\n'
        )

    # Reuse-Session Mode does not support tests using forked subprocesses.
    if "--forked" in sys_argv and ("--rs" in sys_argv or "--reuse-session" in sys_argv):
        raise ImproperlyConfigured(
            "\n\n  Reuse-Session Mode does NOT support forked subprocesses!"
            '\n  (DO NOT combine "--forked" with "--rs"/"--reuse-session"!)\n'
        )

    # parser.addini(
    #     name='used_packs',
    #     help='Report used packages',
    #     type='linelist',
    #     default=[('PYTEST_VERSION', pytest.__version__)]
    # )


# endregion pytest_addoption(parser, pluginmanager)


# region pytest_configure(config)


@hookimpl
def pytest_configure(config: "Config") -> None:
    """
    Allow plugins and conftest files to perform initial configuration.

    This hook is called for every plugin and initial conftest file after command line options have been parsed.
    After that, the hook is called for other conftest files as they are imported.

    :param config: The pytest Config object instance
    """
    config_logger = logger.bind(task="config".rjust(10, " "))

    config_logger.trace("Storing stash key for pytestconfig")
    from sel4.core.runtime import pytestconfig, timeout_changed
    runtime_store[pytestconfig] = config
    runtime_store[timeout_changed] = False

    config_logger.info('Registering "DirectoryManagerPlugin" plugin"')
    from sel4.core.plugins.directory_manager import DirectoryManagerPlugin

    plugin = DirectoryManagerPlugin(config)
    config.pluginmanager.register(plugin, plugin.name)

    if config.getoption("archive_results"):
        config_logger.debug(
            'Option "archive_results" was set, calling [grey66]hook pytest_kiru_archive_results[/]'
        )
        config.hook.pytest_archive_results()
    config_logger.debug("calling hook [grey66]pytest_create_results_directory[/]")
    config.hook.pytest_create_results_directory()
    config_logger.debug('Unregistering "DirectoryManagerPlugin", no longer needed')
    config.pluginmanager.unregister(plugin)
    del plugin

    from sel4.contrib.pytest.utils import collect_metadata

    metadata = collect_metadata(config)
    # metadata.update({k: v for k, v in config.getoption("metadata")})
    # metadata.update(json.loads(config.getoption("metadata_from_json")))
    plugins = defaultdict(lambda: None)
    for plugin, dist in config.pluginmanager.list_plugin_distinfo():
        name, version = dist.project_name, dist.version
        if name.startswith("pytest-"):
            name = name[7:]
        plugins[name] = version
    metadata.plugins = plugins

    from sel4.contrib.pytest.utils.metadata import Metadata

    metadata_key = StashKey[Metadata]
    runtime_store[metadata_key] = metadata

    if not hasattr(config, "workerinput"):
        # prevent opening htmlpath on worker nodes (xdist)
        from sel4.core.plugins.reporter import PyTestReporter

        reporter_plugin = PyTestReporter(config)
        config_logger.debug("Registering PyTestReporter plugin")
        config.pluginmanager.register(reporter_plugin, PyTestReporter.name)
        config.add_cleanup(
            cleanup_factory(pluginmanager=config.pluginmanager, plugin=reporter_plugin)
        )
    else:
        reporter_plugin = PyTestReporterWorker

    # assert_plugin = AssertionPlugin(config)
    # config.pluginmanager.register(assert_plugin, AssertionPlugin.name)
    # get_session_settings().assertion_plugin = assert_plugin

    config_logger.debug('Creating [bold]cache[/bold] folder if not exists"')
    # -- cleaning old cache
    from sel4.contrib.pytest.cache_helper import PytestCache

    ptc = PytestCache(config.cache)
    cache_path = config.rootpath.joinpath(config.getini("cache_dir"))
    config_logger.debug(
        'Cleaning cache dir for files older than 10 days in different thread"'
    )
    from threading import Thread

    thread = Thread(
        target=ptc.delete_cache_older_than_x_days,
        args=(
            cache_path,
            -10,
        ),
    )
    thread.daemon = True
    thread.start()

    # -- registering markers
    config_logger.debug('Registering the following markers:  ["unittest", "testcase"]')
    markers_ini = config.getini("markers")
    if not list(filter(lambda x: x.startswith("unittest"), markers_ini)):
        config.addinivalue_line(
            "markers", "unittest: internal unit-tests for this framework"
        )
    if not list(filter(lambda x: x.startswith("testcase"), markers_ini)):
        config.addinivalue_line(
            "markers", "testcase: connection to zephyr scale test case id"
        )


# endregion pytest_configure(config)


# region pytest_plugin_registered(plugin, manager)


def pytest_plugin_registered(
    plugin: "_PluggyPlugin", manager: "PytestPluginManager"
) -> None:
    """ A new pytest plugin got registered.

    :param plugin: The plugin module or instance.
    :param manager: pytest plugin manager.
    """
    _UNREGISTER_PLUGINS = frozenset(["junitxml", "nose", "logging", "doctest"])
    prefix = "A new pytest plugin got registered -> "
    with logger.contextualize(task="setup".rjust(10, " ")):
        canonical_name = manager.get_canonical_name(plugin)
        name = manager.get_name(plugin)
        if canonical_name == name:
            logger.debug("{} {name}", prefix, name=name)
        else:
            logger.debug(
                "{} {name}/{canonical_name}",
                prefix,
                name=name,
                canonical_name=canonical_name,
            )
    plugin_name = manager.get_name(plugin)
    if plugin_name in _UNREGISTER_PLUGINS:
        #     if settings.DEBUG:
        #         canonical_name = manager.get_canonical_name(plugin)
        #         get_console().log(f'Unregistering plugin: [wheat1]{plugin_name}/{canonical_name}[/]')
        manager.unregister(plugin, plugin_name)


# endregion pytest_plugin_registered(plugin, manager)


# region pytest_sessionstart(session)

if TYPE_CHECKING:
    from pytest import Session


_MARKDOWN = """
PYTEST SESSION STARTED
======================
"""


@hookimpl(trylast=True)
def pytest_sessionstart(session: "Session"):
    from rich.markdown import Markdown

    md = Markdown(_MARKDOWN)
    get_console().print(md, style="bright_blue")
    from sel4.utils.log import setup_session_logger

    # setup_session_logger()
    logger.info("Successfully setup logging configuration for session")


# endregion sessionstart


# region pytest_unconfigure(config)


def pytest_unconfigure(config: "Config") -> None:
    """
    Called before test process is exited.

    :param config:  The pytest config object.
    """
    with logger.contextualize(task="teardown".rjust(10, " ")):
        logger.debug("Unregistering kiru plugins")

        from sel4.core.plugins.directory_manager import DirectoryManagerPlugin

        # pl_names = ['sel4.core.plugins.webdriver', DirectoryManagerPlugin.name, AssertionPlugin.name]
        pl_names = ["sel4.core.plugins.webdriver", DirectoryManagerPlugin.name]
        for pl in pl_names:
            if config.pluginmanager.has_plugin(pl):
                plugin = config.pluginmanager.get_plugin(pl)
                name = config.pluginmanager.get_name(plugin)
                logger.debug("Unregistering plugin: " "[wheat1]{name}[/]", name=name)
                config.pluginmanager.unregister(plugin, pl)


# endregion pytest_unconfigure(config)

########################################################################################################################
# PYTEST HOOKS HELPERS
########################################################################################################################
def _before_hook(hook_name: str, hook_impls: List, kwargs: dict):
    with logger.contextualize(task="setup".rjust(10, " ")):
        if len(hook_impls):
            for hook_impl in hook_impls:
                logger.trace(
                    'hook_name: "{}", plugin: {plugin}\n\tkwargs: {keys}',
                    hook_name,
                    plugin=hook_impl.plugin_name,
                    keys=list(kwargs.keys()),
                )
        else:
            logger.trace(
                'hook_name: "{}", kwargs: {keys}', hook_name, keys=list(kwargs.keys())
            )


def _after_hook(outcome, hook_name: str, hook_impls: List, kwargs: dict):
    with logger.contextualize(task="setup".rjust(10, " ")):
        if len(hook_impls):
            for hook_impl in hook_impls:
                logger.trace(
                    'hook_name: "{}", plugin: {plugin}\n\tkwargs: {keys}',
                    hook_name,
                    plugin=hook_impl.plugin_name,
                    keys=list(kwargs.keys()),
                )
        else:
            logger.trace(
                'hook_name: "{}", kwargs: {keys}', hook_name, keys=list(kwargs.keys())
            )

        if outcome.excinfo:
            logger.error("excinfo: {}", outcome.excinfo)


def cleanup_factory(pluginmanager: "PytestPluginManager", plugin):
    def clean_up():
        name = plugin.name
        pluginmanager.unregister(name=name)

    return clean_up


# endregion PYTEST INITIALIZATION HOOK IMPLEMENTATIONS


########################################################################################################################
# PYTEST COLLECTION HOOK IMPLEMENTATIONS
########################################################################################################################

# region PYTEST INITIALIZATION HOOK IMPLEMENTATIONS

if TYPE_CHECKING:
    from pytest import Collector, Function, Item


# region pytest_pyfunc_call(pyfuncitem)


@hookimpl(hookwrapper=True)
def pytest_pyfunc_call(pyfuncitem: "Function") -> Optional[object]:
    # do_something_before_next_hook_executes()
    outcome = yield
    # outcome.excinfo may be None or a (cls, val, tb) tuple
    res = outcome.get_result()  # will raise if outcome was exception
    # post_process_result(res)
    # outcome.force_result(new_res)


# endregion pytest_pyfunc_call(pyfuncitem)


# region pytest_collectstart(collector)


def pytest_collectstart(collector: "Collector") -> None:
    pass
    # collect_logger = logger.bind(task="collect".rjust(10, " "))
    # collect_logger.trace("Collecting tests on {}", collector.name)
    # collect_logger.debug("Collecting tests on path: {}", str(collector.path))
    # collector.session._collected = Dashboard()


# endregion pytest_collectstart(collector)


# region pytest_item_collected(item)


def pytest_itemcollected(item: "Item"):
    from sel4.core import runtime

    def get_test_ids():
        t_id = item.nodeid.split("/")[-1].replace(" ", "_")
        if "[" in t_id:
            t_id_intro = t_id.split("[")[0]
            param = re.sub(re.compile(r"\W"), "", t_id.split("[")[1])
            t_id = t_id_intro + "__" + param
        d_id = t_id
        from sel4.utils.strutils import multi_replace

        t_id = multi_replace(t_id, [("/", "."), ("\\", "."), ("::", "."), (".py", "")])
        return t_id, d_id

    if item.config.getoption("dashboard", False):
        display_id, test_id = get_test_ids()
        collector = cast(Dashboard, getattr(item.session, "_collected"))
        collector.items_count += 1
        test = TestId(
            result="Not tested",
            duration=0.0,
            display_id=display_id,
            log_path=pathlib.Path("."),
        )
        collector.tests.append(test)


# endregion pytest_item_collected(item)


# region pytest_deselected(items)


def pytest_deselected(items: Sequence["Item"]) -> None:
    """Called for deselected test items, e.g. by keyword."""
    pass
    # if sb_config.dashboard:
    #     sb_config.item_count -= len(items)
    #     for item in items:
    #         test_id, display_id = _get_test_ids_(item)
    #         if test_id in sb_config._results.keys():
    #             sb_config._results.pop(test_id)


# endregion pytest_deselected(items)

# endregion PYTEST INITIALIZATION HOOK IMPLEMENTATIONS


if TYPE_CHECKING:
    from _pytest.fixtures import FixtureRequest


@fixture(name="webdriver_test")
def webdriver_test_fixture(request: "FixtureRequest", cache):
    if not request.config.pluginmanager.has_plugin("sel4.core.plugins.webdriver"):
        from sel4.core.exceptions import ImproperlyConfigured

        raise ImproperlyConfigured(
            "This is not a webdriver session, cannot use this fixture"
        )

    from sel4.core.webdrivertest import WebDriverTest

    wd_class = WebDriverTest.from_parent(request.node, name="webdriver_test")
    wd_class.setup()
    needs_teardown = StashKey[bool]()
    wd_class.stash[needs_teardown] = True

    yield wd_class

    wd_class.teardown()
