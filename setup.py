import sys
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
    setup_requires=['pytest-runner'] if 'test' in sys.argv else [],
    tests_require=['pytest', 'pyshould'],
    version='1.1.1',
    zip_safe=False,
)
