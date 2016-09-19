"""
This file contains tests that use PY3 syntax and would break the parser
if loaded with PY2.

Make sure the test runner doesn't collect this file automatically and that
the symbols in this module are not shadowed by the ones in the main test file.

:copyright: (c) 2013 by Telefonica I+D.
:license: see LICENSE for more details.
"""

from typing import Any

import unittest
from pyshould import should

from di import injector, Key

KeyA = Key('A')
KeyB = Key('B')
KeyC = Key('C')


def test_py3_kwonlydefaults():

    inject = injector({KeyA: 'A', KeyB: 'B', KeyC: 'C'})

    @inject
    def foo(a, b=KeyB, *, c=KeyC):
        return (b, c)

    foo(10) | should.eql(('B', 'C'))

    @inject
    def bar(a, *, b=KeyB):
        return b

    bar(10) | should.eql('B')


def test_py3_annotations():

    class Foo: pass
    class Bar: pass
    class Baz: pass
    class Qux: pass

    inject = injector({Foo: Foo(), Bar: Bar(), Baz: Baz(), Qux: Qux()})

    @inject
    def foo(a: Foo = Key, b: Any = Bar, c: Baz = Baz, d=Qux):
        return (a, b, c, d)

    foo() | should.eql((
        should.be_a(Foo),
        should.be_a(Bar),
        should.be_a(Baz),
        should.be_a(Qux)
    ))

