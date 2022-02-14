import sys

import pytest
from pytest import mark


@mark.parametrize("a, b", [(1, 2), (2, 3)])
def test_b(webdriver_test, a, b):
    print("A")

# @mark.xfail
# def test_function_just_xfail_fail():
#     assert 1 == 2


@mark.xfail
def test_function_just_xfail_pass():
    assert 1 == 1


def test_xfail_internal():
    import pytest
    pytest.xfail("failing configuration (but should work)")


@mark.xfail(sys.platform == "win32", reason="bug in a 3rd party library")
def conditional_xfail():
    pass

xfail = pytest.mark.xfail


@xfail
def test_hello():
    assert 0


@xfail(run=False)
def test_hello2():
    assert 0


@xfail("hasattr(os, 'sep')")
def test_hello3():
    assert 0


@xfail(reason="bug 110")
def test_hello4():
    assert 0


@xfail('pytest.__version__[0] != "17"')
def test_hello5():
    assert 0


def test_hello6():
    pytest.xfail("reason")


@xfail(raises=IndexError)
def test_hello7():
    x = []
    x[1] = 1

#
# @mark.xfail(strict=True)
# def test_function_xfail_strict_true():
#     assert 1 == 2
#
#
# @mark.xfail(strict=False)
# def test_function_xfail_strict_false():
#     assert 1 == 2

# @mark.xfail(strict=True)
# def test_function_xfail():
#     pass
#
# @mark.xfail(strict=True)
# def test_function():
#     pass
#
# @mark.skip(reason="no way of currently testing this")
# def test_the_unknown():
#     print("Skip")
#
#
# @mark.xfail(sys.platform == "win32", reason="bug in a 3rd party library")
# def test_function():
#     print("")
#
# @mark.xfail
# def test_function():
#     print("xfail")
#
#
# @mark.parametrize("a, b", [(1, 2), (2, 3)])
# def test_a(webdriver_test, a, b):
#     print("A")
#
#

#
#
# def test_c(webdriver_test):
#     print("A")
#
#
# def test_d(webdriver_test):
#     print("A")
#
#
# def test_e(webdriver_test):
#     print("A")
