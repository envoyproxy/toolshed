#!/usr/bin/env python

import os
import codecs
from setuptools import setup  # type:ignore


DESCRIPTION = (
    "A patches test fixture which provides a contextmanager for handling "
    "multiple mock patches")


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    return codecs.open(file_path, encoding='utf-8').read()


setup(
    name='mypy-abstracts',
    version=read("VERSION"),
    author='Ryan Northey',
    author_email='ryan@synca.io',
    maintainer='Ryan Northey',
    maintainer_email='ryan@synca.io',
    license='Apache Software License 2.0',
    url='https://github.com/envoyproxy/pytooling/mypy-abstracts',
    description=DESCRIPTION,
    long_description=read('README.rst'),
    py_modules=['mypy_abstracts'],
    python_requires='>=3.5',
    install_requires=['mypy'],
    extras_require={
        "test": [
            "pytest",
            "pytest-coverage"],
        "lint": ['flake8'],
        "publish": ['wheel'],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: Pytest',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Testing',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: Implementation :: CPython',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: Apache Software License',
    ],
)
