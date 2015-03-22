# di-py

Dependency injection library for python.

[![Build Status](https://travis-ci.org/juandebravo/di-py.svg?branch=master)](https://travis-ci.org/juandebravo/di-py)

# Background

Dependency injection *enables us to write better code*, regardless of doing so
manually or with the help of some library. It helps specially to keep our code
inside the [Law of Demeter](http://en.wikipedia.org/wiki/Law_of_Demeter),
by programming against a known interface without having to worry about
how a concrete implementation is composed.

Python offers *decorators*, *metaclasses* and *context managers* (among other
functionalities) as a mean to implement user defined control structures.
They work great to encapsulate patterns, hence complexity, while keeping
a sane separation of concerns.

# Scenarios

* [DI at method level](tests/di_tests.py#L32-L104)
* [DI using descriptor protocol](di/main.py#L217-L221)
* [DI using a metaclass](tests/di_tests.py#L107-L143)

# Install


### Get the latest stable version

```bash
pip install di-py
```

### Get the edge version directly from github

```bash
pip install git+ssh://git@github.com/telefonicaid/di-py.git@master
```

### Using RPM

Generate RPM from source code: Download the code and generate the RPM

```bash
git clone git@github.com/telefonicaid/di-py.git
cd di-py
python setup.py bdist_rpm
```

# License

See [LICENSE](LICENSE)

# Contributing

Use the GitHub's pull request and issue tracker to provide patches or
report problems with the library. All new functionality must be covered
by unit tests before it can be included in the repository.

The develop branch always has the cutting edge version of the code, if
you are using it in your project it would be wise to create a fork of the
repository or target a specific tag/commit for your dependencies.


# Credits

- [Iván -DrSlump- Montes](https://github.com/drslump)
- [Juan de Bravo](https://github.com/juandebravo)
- [Sergi Sorribas](https://github.com/lerovitch)
- [Tomas Montserrat](https://github.com/tomas-mm)
