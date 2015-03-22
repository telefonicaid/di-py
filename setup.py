from setuptools import setup, find_packages

try:
    # HACK: Avoid "TypeError: 'NoneType' object is not callable"
    #      Related to issue http://bugs.python.org/issue15881
    #      https://hg.python.org/cpython/rev/0a58fa8e9bac
    import multiprocessing
except ImportError:
    pass

setup(
    name='di-py',
    description='Dependency injection library',
    version='1.0.3',
    url='https://www.github.com/juandebravo/di-py',
    author='Telefonica Digital',
    author_email='connect-dev@tid.es',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[],
    tests_require=['nose', 'pyshould'],
    test_suite='nose.collector',
    zip_safe=False,
)
