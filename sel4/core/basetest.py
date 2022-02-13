from _pytest import unittest


class BasePytestUnitTestCase(unittest.UnitTestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._called_setup = False
        self._called_teardown = False
        self.__deferred_assert_count = 0
        self.__deferred_assert_failures = []
        self.__visual_baseline_copies = []
