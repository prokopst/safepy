#!/usr/bin/env python
from setuptools import setup, find_packages
import sys
from os import path

if sys.version_info < (3, 5):
    raise RuntimeError("Python < 3.5 is not supported!")

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.rst')) as file:
    long_description = file.read()

setup(
    name='safepy',
    version='0.0.1',
    description="",
    long_description=long_description,
    url='https://github.com/prokopst/safepy',
    packages=find_packages(include=['safepy']),
    author="Stanislav Prokop",
    license='Apache 2 License',
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.5",
    ],
    keywords="safety microservice microservices",
    test_suite='tests',
    setup_requires=['nose']
)
