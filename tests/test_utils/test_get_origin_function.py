# type: ignore
# ruff: noqa
from __future__ import annotations

import functools
import sys
import unittest

from awepatch.utils import get_origin_function


class NTimesUnwrappable:
    def __init__(self, n):
        self.n = n
        self._next = None

    @property
    def __wrapped__(self):
        if self.n <= 0:
            raise Exception("Unwrapped too many times")
        if self._next is None:
            self._next = NTimesUnwrappable(self.n - 1)
        return self._next


class TestUnwrap(unittest.TestCase):
    def test_unwrap_one(self):
        def func(a, b):
            return a + b

        wrapper = functools.lru_cache(maxsize=20)(func)
        self.assertIs(get_origin_function(wrapper), func)

    def test_unwrap_several(self):
        def func(a, b):
            return a + b

        wrapper = func
        for __ in range(10):

            @functools.wraps(wrapper)
            def wrapper():
                pass

        self.assertIsNot(wrapper.__wrapped__, func)
        self.assertIs(get_origin_function(wrapper), func)

    def test_cycle(self):
        def func1():
            pass

        func1.__wrapped__ = func1
        with self.assertRaisesRegex(ValueError, "wrapper loop"):
            get_origin_function(func1)

        def func2():
            pass

        func2.__wrapped__ = func1
        func1.__wrapped__ = func2
        with self.assertRaisesRegex(ValueError, "wrapper loop"):
            get_origin_function(func1)
        with self.assertRaisesRegex(ValueError, "wrapper loop"):
            get_origin_function(func2)

    def test_unhashable(self):
        def func():
            pass

        func.__wrapped__ = None

        class C:
            __hash__ = None
            __wrapped__ = func

        self.assertIsNone(get_origin_function(C()))

    def test_recursion_limit(self):
        obj = NTimesUnwrappable(sys.getrecursionlimit() + 1)
        with self.assertRaisesRegex(ValueError, "wrapper loop"):
            get_origin_function(obj)

    def test_wrapped_descriptor(self):
        self.assertIs(get_origin_function(NTimesUnwrappable), NTimesUnwrappable)
        self.assertIs(get_origin_function(staticmethod), staticmethod)
        self.assertIs(get_origin_function(classmethod), classmethod)
        self.assertIs(get_origin_function(staticmethod(classmethod)), classmethod)
        self.assertIs(get_origin_function(classmethod(staticmethod)), staticmethod)
