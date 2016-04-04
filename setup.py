from setuptools import setup, find_packages

try:
    # HACK: Avoid "TypeError: 'NoneType' object is not callable"
    #      Related to issue http://bugs.python.org/issue15881
    #      https://hg.python.org/cpython/rev/0a58fa8e9bac
    import multiprocessing
except ImportError:
    pass

setup(
    author='Telefonica Digital',
    author_email='connect-dev@tid.es',
    description='Dependency injection library',
    include_package_data=True,
    install_requires=[],
    name='di-py',
    packages=find_packages(exclude=['test*']),
    url='https://www.github.com/telefonicaid/di-py',
    tests_require=['nose', 'pyshould'],
    test_suite='nose.collector',
    version='1.1.0',
    zip_safe=False,
)
