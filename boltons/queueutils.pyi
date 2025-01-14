from typing import Dict, Hashable, Union

from _typeshed import Incomplete

BList: list = list


class BasePriorityQueue:
    _default_priority_key: Union[float, int] = ...
    _backend_type: list = ...

    def __init__(self, **kw: Dict) -> None:
        ...

    def add(self, task: Hashable, priority: Incomplete | None = ...) -> None:
        ...

    def remove(self, task: Hashable) -> None:
        ...

    def peek(self, default=...):
        ...

    def pop(self, default=...):
        ...

    def __len__(self):
        ...


class HeapPriorityQueue(BasePriorityQueue):
    ...


class SortedPriorityQueue(BasePriorityQueue):
    ...


PriorityQueue = SortedPriorityQueue
