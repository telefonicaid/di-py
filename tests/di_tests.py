"""
:copyright: (c) 2013 by Telefonica I+D.
:license: see LICENSE for more details.
"""

import unittest
from pyshould import should

from di import injector, Key, DependencyMap, ContextualDependencyMap, MetaInject

class Ham(object):
    pass

class Spam(object):
    pass


class Eggs(object):
    '''class that has dependencies injected via descriptor'''

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
        foo = self.inject(lambda: True)
        foo() | should.be_True

        foo = self.inject(lambda x: x)
        foo(10) | should.be(10)

    def test_descriptor_no_type_found(self):
        Foo.DEPS.clear()
        Foo.DEPS[InjectorErrorsTests] = self
        with should.throw(LookupError):
            foo = Foo()
            foo.bar()


class InjectorMetaclassTests(unittest.TestCase):

    def setUp(self):
        # Python 3 metaclass syntax is not compatible with Python 2.x
        import sys
        if sys.version_info[0] >= 3:
            from nose.plugins.skip import SkipTest
            raise SkipTest

        self.ham = Ham()
        self.map = {
            Ham: self.ham
        }
        self.inject = injector(self.map)

        class Foo(object):
            __metaclass__ = MetaInject(self.inject)
            def echo(self, test=Ham):
                return test

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


if __name__ == '__main__':
    unittest.main()
