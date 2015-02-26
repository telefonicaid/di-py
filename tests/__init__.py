"""
:copyright: (c) 2013 by Telefonica I+D.
:license: see LICENSE for more details.
"""

import unittest

from .di_tests import (
    InjectorClassTests, InjectorErrorsTests, InjectorMetaclasstests,
    InjectorOverridesTests, InjectorKeyTests, DependencyMapTests,
    ContextualDependencyMapTests
)


def all_tests():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(InjectorClassTests))
    suite.addTest(unittest.makeSuite(InjectorErrorsTests))
    suite.addTest(unittest.makeSuite(InjectorMetaclasstests))
    suite.addTest(unittest.makeSuite(InjectorOverridesTests))
    suite.addTest(unittest.makeSuite(InjectorKeyTests))
    suite.addTest(unittest.makeSuite(DependencyMapTests))
    suite.addTest(unittest.makeSuite(ContextualDependencyMapTests))
    return suite
