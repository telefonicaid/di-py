"""
Dependency injection utilities

:copyright: (c) 2013-15 by Telefonica I+D.
:license: see LICENSE.txt for more details.

Python is a highly dynamic language with an "open class" implementation for user
types, thus the need for a full blown dependency injection framework is not
specially needed. For medium to large applications though there is still the
issue of how to actually implement dependency injection in the code using only
Python's standard syntax/library.

The following tools are designed to be very lightweight and flexible as to allow
their use in a variety of scenarios, including their use to aid with unit testing.
It doesn't form a *framework* but just a set of utilities to keep the dependency
injection needs in a project under control by applying it only where it makes
sense, with minimum overhead and a lean learning curve.
"""
import sys
import logging
import inspect
import functools

import threading
try:
    import thread
except ImportError:
    # Python 3.3 exposes .get_ident on the threading module
    thread = threading

PY2 = sys.version_info[0] == 2

logger = logging.getLogger(__name__)


class Key(object):
    """ Wraps a value to be used as key with the injector decorator.

        In some cases it may be needed to map a dependency injection to something
        other than a class. For instance, we might want to make some value
        injectable based on a string identifier.
        For those cases this class can be used to indicate the decorator that it
        should look in the mapping for the wrapped value.

            inject = injector({ 'foo': 'FOO' })

            @inject
            def foo(msg=Key('foo')):
                print msg
    """
    def __init__(self, value, *values):
        if len(values):
            self.value = (value,) + values
        else:
            self.value = value

    def __eq__(self, other):
        if isinstance(other, Key):
            return self.value == other.value
        return self.value == other

    def __ne__(self, other):
        if isinstance(other, Key):
            return self.value != other.value
        return self.value != other


def injector(dependencies):
    """ Factory for the dependency injection decorator. It's meant to be
        initialized with the map of dependencies to use on decorated functions.

            inject = injector({
                ConfigManager: ConfigManager('settings.cfg'),
                Redis: Redis('127.0.0.1')
            })

            @inject
            def process(queue, config=ConfigManager, redis=Redis):
                return redis.hmget(config['info_key'])

        Dependency resolution is very straightforward, no inheritance is taken
        into account, the dependency map must be initialized with the actual
        classes used to annotate the decorated functions.

        When a decorated method defines a dependency not correctly configured
        in the map it will raise a LookupError to indicate so.

        Note that the dependency map can be updated at any time, affecting
        following calls to decorated methods.

        A common pattern is to apply dependency injection only when instantiating
        a class. This can be easily accomplish by decorating the class' __init__
        method, storing injected values as object attributes.

            @inject
            def __init__(self, config=ConfigManager):
                self._config = config

        If you see a TypeError with the message 'got multiple values for keyword
        argument', make sure that all calls to the decorated method always use
        keyword arguments for injected values. Use of positional injected arguments
        is not supported.
    """

    def wrapper(fn):
        # Extract default values for keyword arguments
        args, varargs, keywords, defaults = inspect.getargspec(fn)
        if defaults:
            defaults = dict(zip(reversed(args), reversed(defaults)))
        else:
            defaults = {}

        # Mapping for injectable values (classes used as default value)
        mapping = {}
        for name, default in defaults.items():
            if isinstance(default, Key):
                mapping[name] = default.value
            elif inspect.isclass(default):
                mapping[name] = default

        if not mapping:
            logger.debug('%s: No injectable params found. You can safely remove the decorator.',
                         fn.__name__)
            return fn

        # Micro optimization: prepare mapping as a list of pairs
        pairs = mapping.items()

        # Wrapper executed on each invocation of the decorated method
        @functools.wraps(fn)
        def inner(*args, **kwargs):
            # Micro optimization: cache logger level
            debug = logger.isEnabledFor(logging.DEBUG)

            # Iterate over the set of 'injectable' parameters
            for name, key in pairs:
                # If the argument was not explicitly given inject it
                if name not in kwargs:
                    debug and logger.debug('%s: Injecting %s with %s', fn.__name__, name, key)
                    # Avoid using `in` operator to check, so we can work with
                    # maps not supporting __contain__
                    try:
                        kwargs[name] = wrapper.dependencies[key]
                    except KeyError:
                        raise LookupError('Unable to find an instance for {0} when calling {1}'.format(
                            key, fn.__name__))

            return fn(*args, **kwargs)

        return inner

    # Expose the dependency map publicly in the decorator
    wrapper.dependencies = dependencies

    return wrapper


def MetaInject(injector):
    """
        Builds a metaclass with the *injector* parameter as dependecy injector.
    """

    def is_user_function(name, fn):
        """ Checks that a function isn't named as an operator overload (__name__) """
        return callable(fn) and name[:2] != '__' and name[-2:] != '__'

    class ActualMetaInject(type):
        """
            Metaclass to define the dependency injection in a class level instead
            of requiring the decorator definition in every instance method.
            This might be used in classes that injects dependencies for most of
            their methods.

            class Foo(object):
                __metaclass__ = MetaInject(inject)

                # this method will be automatically decorated with `inject`
                def foo(self, redis=Redis):
                    pass
        """

        def __new__(cls, name, bases, dct):
            """
                Generates a new instance including the injector factory for every
                method except for *operator overloads*.
            """

            # Filter methods to be decorated
            methods = ((k, v) for (k, v) in dct.items() if is_user_function(k, v))

            for m, fn in methods:
                dct[m] = injector(fn)

            return type.__new__(cls, name, bases, dct)

    return ActualMetaInject


class DependencyMap(object):
    """
        Implements the "dict" protocol for the dependencies but applies
        custom logic on how to obtain them based on the configured flags:

            FACTORY: obtain the value by executing a function
            SINGLETON: only execute the factory once
            THREAD: only execute the factory once for each unique thread
    """

    NONE = 0
    FACTORY = 1
    SINGLETON = 2
    THREAD = 4

    def __init__(self, *args, **kwargs):
        self._values = dict(*args, **kwargs)
        self._flags = {}
        self._singletons = {}
        self._threadlocals = threading.local()

    def __call__(self, key):
        """ descriptor factory method.
            >>> dm = DependencyMap()
            >>> class Bar(object):
                    pass
            >>> class Foo(object):
                    my_injected_dep = dm(Spam)
        """
        return InjectorDescriptor(key, self)

    def __getitem__(self, key):
        # Unwrap Key instances
        if isinstance(key, Key):
            key = key.value

        value = self._values[key]
        flags = self._flags.get(key, DependencyMap.NONE)

        # HACK: Somewhat complex code but we strive for performance here
        try:
            if flags & DependencyMap.FACTORY:
                if flags & DependencyMap.SINGLETON:
                    if key not in self._singletons:
                        logger.debug('Running singleton factory for dependency %s', key)
                        self._singletons[key] = value(self)
                    value = self._singletons[key]
                elif flags & DependencyMap.THREAD:
                    if not hasattr(self._threadlocals, key):
                        logger.debug('Running thread factory for dependency %s in thread (%d)',
                                     key, thread.get_ident())
                        setattr(self._threadlocals, key, value(self))
                    value = getattr(self._threadlocals, key)
                else:
                    logger.debug('Running factory for dependency %s', key)
                    value = value(self)
        except Exception as e:
            # factory method's exceptions might occur at devel time,
            # better to log them in an unpleasant way to fix them quickly
            logger.exception('Unexpected problem when creating an instance')
            raise e

        return value

    def __setitem__(self, key, value):
        # Make sure we remove any flags associated with the key
        if key in self._flags:
            del self._flags[key]

        self._values[key] = value

    def __contains__(self, key):
        # Unwrap Key instances
        if isinstance(key, Key):
            key = key.value

        return key in self._values

    def proxy(self, key):
        """ Proxy factory method.

            >>> dm = DependencyMap()
            >>> my_injected_dep = dm.proxy(Spam)
        """
        return InjectorProxy(self, key)

    def register(self, key, value, flags=NONE):
        """ Register a new dependency optionally giving it a set of flags
        """
        logger.debug('Registered %s with flags=%d', key, flags)
        # Unwrap Key instances
        if isinstance(key, Key):
            key = key.value

        self._values[key] = value
        self._flags[key] = flags

    def factory(self, key, flags=NONE):
        """ Factory decorator to register functions as dependency factories
        """
        def decorator(fn):
            self.register(key, fn, flags | DependencyMap.FACTORY)

        return decorator

    def singleton(self, key):
        return self.factory(key, flags=DependencyMap.SINGLETON)

    def thread(self, key):
        return self.factory(key, flags=DependencyMap.THREAD)


class ContextualDependencyMap(DependencyMap):
    """ Specialized dependency map to support scenarios where different
        dependency instances should be used based on some context.

        Provisioning of dependencies is only done once but allows to
        execute singleton/thread factory functions for every different
        context. For instance, when a language setting is used this can
        help organize the dependencies with factories depending on it.
    """

    def __init__(self, *args, **kwargs):
        super(ContextualDependencyMap, self).__init__(*args, **kwargs)
        self._maps = {}
        self.map = self

    def context(self, context):
        """ Changes the current context for the dependencies returning the
            child dependency map corresponding to the given context.
            New context values will automatically create a child dependency map
            associated with it.
            This method will return the selected dependency map instance.
        """
        # If no context is given the context-less map is activated
        if context is None:
            self.map = self
            return self.map

        # Every new context is associated with an isolated dependency
        # map, which is initialized with the current state for the root map.
        if context not in self._maps:
            logger.debug('Initializing dependency map for context: %s', context)
            self._maps[context] = DependencyMap()
            for k, v in self._values.items():
                self._maps[context].register(k, v, self._flags.get(k, DependencyMap.NONE))

        logger.debug('Switched dependency map context to: %s', context)
        self.map = self._maps[context]
        return self.map

    def reset(self):
        """ Destroys any reference to specific contexts. This method is specially
            suited for unit testing.
        """
        self._maps = {}
        self.context(None)

    def __getitem__(self, key):
        if self.map is self:
            return super(ContextualDependencyMap, self).__getitem__(key)
        # Forward the query to the current context's map
        return self.map[key]

    def __setitem__(self, key, value):
        """ When setting a value it's assigned to the current map
        """
        if self.map is self:
            super(ContextualDependencyMap, self).__setitem__(key, value)
        else:
            self.map[key] = value

    def __contains__(self, key):
        if self.map is self:
            return super(ContextualDependencyMap, self).__contains__(key)
        return key in self.map


class PatchedDependencyMap(object):
    """ Serves the purpose of overriding values from a dependency map. Specially useful for
        modifying dependencies while testing.

            def setUp(self):
                # Replace the map in the inject decorator with a patched one
                deps = PatchedDependencyMap(inject.dependencies)
                inject.dependencies = deps
                deps[ConfigManager] = mock()

            def tearDown(self):
                # Restore original dependency map
                inject.dependencies = inject.dependencies.target
    """
    def __init__(self, depsmap):
        self.target = depsmap
        self._patched = {}

    def __getitem__(self, key):
        """ This is hacky and easy to break so tread lightly. The purpose is to hijack the getter
            in the target dependency map so that dependency hierarchies can also look up into
            patched ones.
        """
        # HACK: Note that we have to override the getter in the class and not the instance
        #       Python will ignore an overridden __getitem__ set on the instance object, calling
        #       always the unbound class method.
        target_cls = self.target.__class__
        target_getter = target_cls.__getitem__

        def getter(inst, key):
            if key in self._patched:
                return self._patched[key]
            return target_getter(inst, key)

        try:
            target_cls.__getitem__ = getter
            return getter(self.target, key)
        finally:
            target_cls.__getitem__ = target_getter

    def __setitem__(self, key, value):
        # Unwrap Key instances
        if isinstance(key, Key):
            key = key.value
        self._patched[key] = value

    def __contains__(self, key):
        return (key in self._patched) or (key in self.target)

    def __getattr__(self, key):
        """ Forward attribute access to the target map
        """
        return getattr(self.target, key)

    def copy(self):
        """ expose dict method to help with mocking frameworks """
        return self._patched.copy()

    def update(self, *args, **kwargs):
        """ expose dict method to help with mocking frameworks """
        self._patched.update(*args, **kwargs)

    def clear(self):
        """ expose dict method to help with mocking frameworks """
        self._patched.clear()


class InjectorDescriptor(object):
    """alternate way of using the injector with a descriptor

        >>> dm = DependencyMap()
        >>> class MyClass(object):
                myfoo = dm(FOO)
        >>> 'when unit testing just clear the singletons dict'
        >>> class FooTestCase(unittest.TestCase):
                def setUp():
                    dm._singletons.clear()
    """

    def __init__(self, class_obj, dependencies):
        self.class_obj = class_obj
        self.dependencies = dependencies

    def __get__(self, inst, cls):
        # Dependency map already introduces a caching mechanism, no need
        # to insert the resolved dependency into the instance.
        # If wanted, just iterate the cls.__dict__ looking for the key to
        # the descriptor with same id as self
        try:
            return self.dependencies[self.class_obj]
        except KeyError:
            raise LookupError('Unable to find an instance for {0}'.format(self.class_obj))


class InjectorProxy(object):
    """
    Alternate way of using the injector with a Proxy

        >>> dm = DependencyMap()
        >>> myfoo = dm.proxy(FOO)

    This code is based on the LocalProxy implemented by Werkzeug
    https://github.com/pallets/werkzeug/blob/master/werkzeug/local.py#L254
    """
    __slots__ = ('__dependencies', '__class_obj', '__dict__')

    def __init__(self, dependencies, class_obj):
        object.__setattr__(self, '_InjectorProxy__dependencies', dependencies)
        object.__setattr__(self, '_InjectorProxy__class_obj', class_obj)

    def _get_current_object(self):
        try:
            return self.__dependencies[self.__class_obj]
        except KeyError:
            raise LookupError('Unable to find an instance for {0}'.format(self.__class_obj))

    @property
    def __dict__(self):
        return self._get_current_object().__dict__

    def __repr__(self):
        return repr(self._get_current_object())

    def __bool__(self):
        return bool(self._get_current_object())

    def __unicode__(self):
        return unicode(self._get_current_object())

    def __dir__(self):
        return dir(self._get_current_object())

    def __getattr__(self, name):
        return getattr(self._get_current_object(), name)

    def __setitem__(self, key, value):
        self._get_current_object()[key] = value

    def __delitem__(self, key):
        del self._get_current_object()[key]

    if PY2:
        __getslice__ = lambda x, i, j: x._get_current_object()[i:j]

        def __setslice__(self, i, j, seq):
            self._get_current_object()[i:j] = seq

        def __delslice__(self, i, j):
            del self._get_current_object()[i:j]

    __setattr__ = lambda x, n, v: setattr(x._get_current_object(), n, v)
    __delattr__ = lambda x, n: delattr(x._get_current_object(), n)
    __str__ = lambda x: str(x._get_current_object())
    __lt__ = lambda x, o: x._get_current_object() < o
    __le__ = lambda x, o: x._get_current_object() <= o
    __eq__ = lambda x, o: x._get_current_object() == o
    __ne__ = lambda x, o: x._get_current_object() != o
    __gt__ = lambda x, o: x._get_current_object() > o
    __ge__ = lambda x, o: x._get_current_object() >= o
    __cmp__ = lambda x, o: cmp(x._get_current_object(), o)
    __hash__ = lambda x: hash(x._get_current_object())
    __call__ = lambda x, *a, **kw: x._get_current_object()(*a, **kw)
    __len__ = lambda x: len(x._get_current_object())
    __getitem__ = lambda x, i: x._get_current_object()[i]
    __iter__ = lambda x: iter(x._get_current_object())
    __contains__ = lambda x, i: i in x._get_current_object()
    __add__ = lambda x, o: x._get_current_object() + o
    __sub__ = lambda x, o: x._get_current_object() - o
    __mul__ = lambda x, o: x._get_current_object() * o
    __floordiv__ = lambda x, o: x._get_current_object() // o
    __mod__ = lambda x, o: x._get_current_object() % o
    __divmod__ = lambda x, o: x._get_current_object().__divmod__(o)
    __pow__ = lambda x, o: x._get_current_object() ** o
    __lshift__ = lambda x, o: x._get_current_object() << o
    __rshift__ = lambda x, o: x._get_current_object() >> o
    __and__ = lambda x, o: x._get_current_object() & o
    __xor__ = lambda x, o: x._get_current_object() ^ o
    __or__ = lambda x, o: x._get_current_object() | o
    __div__ = lambda x, o: x._get_current_object().__div__(o)
    __truediv__ = lambda x, o: x._get_current_object().__truediv__(o)
    __neg__ = lambda x: -(x._get_current_object())
    __pos__ = lambda x: +(x._get_current_object())
    __abs__ = lambda x: abs(x._get_current_object())
    __invert__ = lambda x: ~(x._get_current_object())
    __complex__ = lambda x: complex(x._get_current_object())
    __int__ = lambda x: int(x._get_current_object())
    __long__ = lambda x: long(x._get_current_object())  # noqa
    __float__ = lambda x: float(x._get_current_object())
    __oct__ = lambda x: oct(x._get_current_object())
    __hex__ = lambda x: hex(x._get_current_object())
    __index__ = lambda x: x._get_current_object().__index__()
    __coerce__ = lambda x, o: x._get_current_object().__coerce__(x, o)
    __enter__ = lambda x: x._get_current_object().__enter__()
    __exit__ = lambda x, *a, **kw: x._get_current_object().__exit__(*a, **kw)
    __radd__ = lambda x, o: o + x._get_current_object()
    __rsub__ = lambda x, o: o - x._get_current_object()
    __rmul__ = lambda x, o: o * x._get_current_object()
    __rdiv__ = lambda x, o: o / x._get_current_object()
    if PY2:
        __rtruediv__ = lambda x, o: x._get_current_object().__rtruediv__(o)
    else:
        __rtruediv__ = __rdiv__
    __rfloordiv__ = lambda x, o: o // x._get_current_object()
    __rmod__ = lambda x, o: o % x._get_current_object()
    __rdivmod__ = lambda x, o: x._get_current_object().__rdivmod__(o)
    __copy__ = lambda x: copy.copy(x._get_current_object())
    __deepcopy__ = lambda x, memo: copy.deepcopy(x._get_current_object(), memo)
