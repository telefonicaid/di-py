"""
:copyright: (c) 2013 by Telefonica I+D.
:license: see LICENSE for more details.
"""

import unittest

from .di_tests import (
    InjectorClassTests, InjectorErrorsTests, InjectorMetaclassTests,
    InjectorOverridesTests, InjectorKeyTests, DependencyMapTests,
    DependencyMapDescriptorTests, ContextualDependencyMapTests
)


def all_tests():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(InjectorClassTests))
    suite.addTest(unittest.makeSuite(InjectorErrorsTests))
    suite.addTest(unittest.makeSuite(InjectorMetaclassTests))
    suite.addTest(unittest.makeSuite(InjectorOverridesTests))
    suite.addTest(unittest.makeSuite(InjectorKeyTests))
    suite.addTest(unittest.makeSuite(DependencyMapTests))
    suite.addTest(unittest.makeSuite(DependencyMapDescriptorTests))
    suite.addTest(unittest.makeSuite(ContextualDependencyMapTests))
    return suite
