from pytest import Config, Stash, StashKey
from selenium.webdriver.remote.webdriver import WebDriver

from sel4.utils.typeutils import OptionalFloat

runtime_store = Stash()
pytestconfig = StashKey[Config]()
timeout_changed = StashKey[bool]()
shared_driver = StashKey[WebDriver]()
time_limit = StashKey[OptionalFloat]()
start_time_ms = StashKey[int]()
