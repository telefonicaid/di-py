"""
:copyright: (c) 2013 by Telefonica I+D.
:license: see LICENSE for more details.
"""

import sys
import warnings

import unittest
import pytest
from pyshould import should

from di import injector, Key, DependencyMap, ContextualDependencyMap, PatchedDependencyMap, MetaInject

PY3 = sys.hexversion >= 0x03000000
PY35 = sys.hexversion >= 0x03050000

# Import tests using Python3 syntax when >=3.5
if PY35:
    from .py3 import *


class Ham(object):
    pass


class Spam(object):
    pass


class Eggs(object):
    """class that has dependencies injected via descriptor"""

    DEPS = DependencyMap()

    @DEPS.singleton(Spam)
    def factory_egg(deps):
        return Spam()

    test_descriptor = DEPS(Spam)
    missing_descriptor = DEPS(DependencyMap)

    def bar(self):
        return self.test_descriptor


class Foo(object):
    DEPS = {}
    inject = injector(DEPS)

    @inject
    def __init__(self, test=unittest.TestCase):
        self.test = test

    @inject
    def foo(self, test=unittest.TestCase):
        return test


class InjectorClassTests(unittest.TestCase):

    def test_class_constructor(self):
        Foo.DEPS[unittest.TestCase] = self
        foo = Foo()
        foo.test | should.be(self)

    def test_class_method(self):
        Foo.DEPS[unittest.TestCase] = self
        foo = Foo()
        foo.foo() | should.be(self)
        foo.foo(test=None) | should.be_None

    def test_class_descriptor(self):
        egg = Eggs()
        spam = egg.bar()
        spam | should.be_a(Spam)
        spam_again = egg.bar()
        spam_again | should.be(spam)
        egg.bar() | should.be(spam)


class InjectorErrorsTests(unittest.TestCase):

    def setUp(self):
        self.inject = injector({
            unittest.TestCase: self
        })

    def test_using_injector_as_decorator(self):
        with should.throw(RuntimeError):
            @injector
            def foo(): pass

    def test_missing_dependency(self):
        @self.inject
        def foo(missing=InjectorErrorsTests):
            pass

        with should.throw(LookupError):
            foo()

    def test_missing_dependency_descriptor(self):
        egg = Eggs()
        with should.throw(LookupError):
            egg.missing_descriptor

    def test_positional_arg(self):
        foo = self.inject(lambda param=unittest.TestCase: None)
        with should.throw(TypeError):
            foo(self)

    def test_no_injectable_params(self):
        foo = self.inject(lambda: True, __warn__=False)
        foo() | should.be_True

        foo = self.inject(lambda x: x, __warn__=False)
        foo(10) | should.be(10)

    def test_warns_when_unneeded(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            foo = self.inject(lambda: True)

            w | should.have_len(1)
            w[0].category | should.be(UserWarning)

    def test_descriptor_no_type_found(self):
        Foo.DEPS.clear()
        Foo.DEPS[InjectorErrorsTests] = self
        with should.throw(LookupError):
            foo = Foo()
            foo.bar()


@pytest.mark.skipif(PY3, reason='requires python 2.x (meta-class syntax changes)')
class InjectorMetaclassTests(unittest.TestCase):

    def setUp(self):
        self.ham = Ham()
        self.map = {
            Ham: self.ham
        }
        self.inject = injector(self.map)

        class Foo(object):
            __metaclass__ = MetaInject(self.inject)

            def echo(self, test=Ham):
                return test

            def nouse(self):
                pass

        self.foo = Foo()

    def test_inject_metaclass_default_value(self):
        self.foo.echo() | should.be(self.ham)

    def test_inject_metaclass_override_from_calling_site(self):
        self.foo.echo(test="bar") | should.eql("bar")

    def test_inject_metaclass_keeps_other_decorators(self):
        def upper(fn):
            def inner(*args, **kwargs):
                value = fn(*args, **kwargs)
                return value.upper()
            return inner

        class Foo(object):
            __metaclass__ = MetaInject(self.inject)

            @upper
            def echo(self, test=unittest.TestCase):
                return test

        Foo().echo(test="bar") | should.eql("BAR")

    def test_no_warns_when_unneeded(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            class NoUse(object):
                __metaclass__ = MetaInject(self.inject)

                def foo(self):
                    pass

            NoUse()

            w | should.have_len(0)


class InjectorOverridesTests(unittest.TestCase):

    def setUp(self):
        self.map = {
            unittest.TestCase: self,
        }
        self.inject = injector(self.map)

    def test_override_from_calling_site(self):
        @self.inject
        def foo(test=unittest.TestCase):
            return test

        foo() | should.be(self)
        foo(test=True) | should.be_True

    def test_override_missing(self):
        @self.inject
        def foo(test=unittest.TestCase, missing=InjectorOverridesTests):
            return missing

        foo(missing=self) | should.be(self)

    def test_override_from_updated_map(self):
        @self.inject
        def foo(test=unittest.TestCase):
            return test

        foo() | should.be(self)
        self.map[unittest.TestCase] = True
        foo() | should.be_True

    def test_override_injector_unitestingmode(self):
        egg = Eggs()
        spam = egg.bar()
        spam | should.be_a(Spam)
        spam_again = egg.bar()
        spam_again | should.be(spam)

        # without unit testing the instance keeps the first assignment
        spam = egg.bar()
        Eggs.DEPS._singletons.clear()
        egg = Eggs()
        spam_again = egg.bar()
        spam_again | should.not_be(spam)


class InjectorPatchTests(unittest.TestCase):

    def setUp(self):
        self.map = {
            InjectorPatchTests: self,
        }
        self.inject = injector(self.map)

    def test_patch_hides_previous_deps(self):

        @self.inject
        def test(foo=InjectorPatchTests): pass

        self.inject.patch({})
        with should.throw(LookupError):
            test()

        self.inject.unpatch()
        test()

    def test_patch_multiple(self):
        @self.inject
        def test(foo=InjectorPatchTests):
            return foo

        self.inject.patch({InjectorPatchTests: 1})
        self.inject.patch({InjectorPatchTests: 2})
        self.inject.patch({InjectorPatchTests: 3})

        test() | should.eql(3)
        self.inject.unpatch()
        test() | should.eql(2)
        self.inject.unpatch()
        test() | should.eql(1)
        self.inject.unpatch()
        test() | should.eql(self)

    def test_unpatch_error(self):
        self.inject.patch({})
        self.inject.unpatch()

        with should.throw(RuntimeError):
            self.inject.unpatch()

    def test_deprecated_property(self):
        @self.inject
        def test(foo=InjectorPatchTests):
            return foo

        self.inject.dependencies = {InjectorPatchTests: 'foo'}

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            test() | should.eql('foo')

            w | should.have_len(1)
            w[0].category | should.be(UserWarning)



class InjectorKeyTests(unittest.TestCase):

    def setUp(self):
        self.inject = injector({
            unittest.TestCase: self,
            'foo': 'FOO',
            self: 'SELF',
            (dict, 'foo'): 'SELF-FOO'
        })

    def test_keyed_literal(self):
        @self.inject
        def foo(foo=Key('foo')):
            return foo

        foo() | should.eq('FOO')

    def test_keyed_value(self):
        @self.inject
        def foo(foo=Key(self)):
            return foo

        foo() | should.eq('SELF')

    def test_keyed_multiple(self):
        @self.inject
        def foo(foo=Key(dict, 'foo')):
            return foo

        foo() | should.eq('SELF-FOO')


class DependencyMapTests(unittest.TestCase):

    def setUp(self):
        self.map = DependencyMap()
        self.cnt = 0

    def test_setter(self):
        self.map['foo'] = 'FOO'
        self.map['foo'] | should.eq('FOO')

    def test_register_value(self):
        self.map.register('foo', 'FOO')
        self.map['foo'] | should.eq('FOO')

    def test_register_factory(self):
        @self.map.factory('foo')
        def fn(deps):
            self.cnt += 1
            return self.cnt

        self.map['foo'] | should.eq(1)
        self.map['foo'] | should.eq(2)

    def test_register_singleton(self):
        @self.map.singleton('foo')
        def fn(deps):
            self.cnt += 1
            return self.cnt

        self.map['foo'] | should.eq(1)
        self.map['foo'] | should.eq(1)

    def test_register_thread(self):
        @self.map.thread('foo')
        def fn(deps):
            self.cnt += 1
            return self.cnt

        self.map['foo'] | should.eq(1)
        self.cnt | should.eq(1)
        self.map['foo'] | should.eq(1)
        self.cnt | should.eq(1)

        # Run in a separate thread and make sure the cnt is updated
        import threading
        t1 = threading.Thread(target=lambda: self.map['foo'])
        t1.start()
        t1.join()
        self.cnt | should.eq(2)

    def test_dependencies_passed_as_arg(self):
        self.map.register('dep', 'DEP')

        @self.map.factory('foo')
        def fn(deps):
            return deps['dep']

        self.map['foo'] | should.eq('DEP')

    def test_context_manager(self):
        self.map[Ham] = 10
        self.map[Spam] = 20

        @injector(self.map)
        def func(ham=Ham, spam=Spam):
            return ham + spam

        func() | should.eql( 30 )

        with self.map:
            self.map[Ham] = 1
            func() | should.eql( 21 )

        func() | should.eql( 30 )


class DependencyMapDescriptorTests(unittest.TestCase):

    def test_acts_as_descriptor(self):
        dm = DependencyMap()
        dm[Ham] = Ham()
        dm[Spam] = Spam()

        class Subject:
            ham = dm(Ham)
            spam = dm(Spam)

        subject = Subject()
        subject.ham | should.be_a(Ham)
        subject.spam | should.be_a(Spam)

        dm[Ham] = None
        subject.ham | should.be_None


class DependencyMapProxyTests(unittest.TestCase):

    def test_acts_as_proxy(self):
        dm = DependencyMap()
        dm[Ham] = Ham()
        dm[Spam] = Spam()

        ham = dm.proxy(Ham)
        spam = dm.proxy(Spam)

        ham | should.be_a(Ham)
        spam | should.be_a(Spam)

    def test_proxy_bypassed_methods(self):
        dm = DependencyMap()
        dm[list] = list()

        l = dm.proxy(list)
        l.append(1)
        l.append(3)
        l[1] = 2

        l[0] | should.eq(1)
        l[1] | should.eq(2)
        len(l) | should.eq(2)
        (l == [1, 2]) | should.eq(True)
        repr(l) | should.eq("[1, 2]")
        str(l) | should.eq("[1, 2]")
        (l + [3, 4]) | should.eq([1, 2, 3, 4])

    def test_proxy_reflects_changes(self):
        dm = DependencyMap()
        dm[Ham] = Ham()

        ham = dm.proxy(Ham)
        ham | should.be_a(Ham)

        dm[Ham] = Spam()
        ham | should.be_a(Spam)

    def test_proxy_dependency_missing(self):
        dm = DependencyMap()
        l = dm.proxy("hi")
        with should.throw(LookupError):
            l.foo()

    def test_proxy_support_contextual(self):
        self.cnt = 0

        dm = ContextualDependencyMap()

        @dm.singleton(Ham)
        def difunc(ham):
            self.cnt += 1
            return self.cnt

        ham = dm.proxy(Ham)
        assert ham == 1
        assert ham == 1

        dm.context('es')
        assert ham == 2
        assert ham == 2

        dm.context(None)
        assert ham == 1


class ContextualDependencyMapTests(unittest.TestCase):

    def setUp(self):
        self.map = ContextualDependencyMap()
        self.cnt = 0

    def test_setter(self):
        self.map['foo'] = 'FOO'
        self.map['foo'] | should.eq('FOO')
        self.map.context('A')
        self.map['foo'] | should.eq('FOO')

    def test_factory_in_different_context(self):
        @self.map.factory('foo')
        def fn(deps):
            self.cnt += 1
            return self.cnt

        self.map['foo'] | should.eq(1)
        self.map['foo'] | should.eq(2)
        self.map.context('A')
        self.map['foo'] | should.eq(3)
        self.map['foo'] | should.eq(4)

    def test_singleton_in_different_context(self):
        @self.map.singleton('foo')
        def fn(deps):
            self.cnt += 1
            return self.cnt

        self.map['foo'] | should.eq(1)

        self.map.context('A')
        self.map['foo'] | should.eq(2)

        self.map.context('B')
        self.map['foo'] | should.eq(3)

        self.map.context('A')
        self.map['foo'] | should.eq(2)

    def test_activate_contextmanager(self):
        @injector(self.map)
        def test(foo=Key('foo')):
            return foo

        self.map['foo'] = 'ROOT'

        test() | should.eql('ROOT')
        with self.map.activate('A'):
            self.map['foo'] = 'A'
            test() | should.eql('A')

        test() | should.eql('ROOT')
        with self.map.activate('B'):
            self.map['foo'] = 'B'
            test() | should.eq('B')

            # Force a context
            self.map.context('A')
            test() | should.eq('A')

        test() | should.eql('ROOT')
        with self.map.activate('A'):
            with self.map.activate('B'):
                test() | should.eq('B')
            test() | should.eq('A')

        test() | should.eql('ROOT')

class PatchedDependencyMapTests(unittest.TestCase):
    """
    PatchedDependencyMap is mostly useful for testing with mocks
    """

    def setUp(self):
        self.map = ContextualDependencyMap()
        self.map[ContextualDependencyMap] = self.map
        self.inject = injector(self.map)

        @self.map.singleton(Ham)
        def fn(deps):
            return Ham()

    def test_unpatched(self):
        @self.inject
        def check_instance(ham=Ham):
            ham | should.be_instance_of(Ham)

        check_instance()

    def test_patched(self):
        class Mock(object):
            pass

        patched_map = PatchedDependencyMap(self.map)
        self.inject.patch(patched_map)

        patched_map[Ham] = Mock()

        @self.inject
        def check_instance(ham=Ham):
            ham | should.be_instance_of(Mock)

        check_instance()


if __name__ == '__main__':
    unittest.main()
