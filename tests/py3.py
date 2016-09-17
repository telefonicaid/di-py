"""
This file contains tests that use PY3 syntax and would break the parser
if loaded with PY2.

Make sure the test runner doesn't collect this file automatically and that
the symbols in this module are not shadowed by the ones in the main test file.

:copyright: (c) 2013 by Telefonica I+D.
:license: see LICENSE for more details.
"""

import unittest
from pyshould import should

from di import injector, Key

KeyA = Key('A')
KeyB = Key('B')
KeyC = Key('C')


def test_py3_kwonly():

    inject = injector({KeyA: 'A', KeyB: 'B', KeyC: 'C'})

    # While we don't fix the inject decorator we'll receive an error
    with should.throw(ValueError):
        @inject
        def foo(a, b=KeyB, *args, c=KeyC):
            pass


