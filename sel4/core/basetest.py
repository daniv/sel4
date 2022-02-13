from _pytest import unittest


class BasePytestUnitTestCase(unittest.UnitTestCase):
    def __init__(self, name: str):
        super().__init__(name)
        self.__called_setup = False
        self.__called_teardown = False




