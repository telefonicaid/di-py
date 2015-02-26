from setuptools import setup, find_packages

setup(
    name='di',
    description='Dependency injection library',
    version='{VERSION}',
    url='https://www.github.com/telefonicadigital/di',
    author='Telefonica Digital',
    author_email='connect-dev@tid.es',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[],
    tests_require=['nose', 'pyshould'],
    test_suite='nose.collector',
    zip_safe=False,
)
