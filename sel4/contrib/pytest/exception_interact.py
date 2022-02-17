from typing import Any

from pytest import Item, Collector, CollectReport, TestReport, CallInfo


def item_exception_interact(
        node: Item,
        call: CallInfo[Any],
        report: TestReport
) -> None:
    print("A")