#!/usr/bin/env python

import os
import codecs
from setuptools import find_namespace_packages, setup  # type:ignore


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    return codecs.open(file_path, encoding='utf-8').read()


setup(
    name='abstracts',
    version=read("VERSION"),
    author='Ryan Northey',
    author_email='ryan@synca.io',
    maintainer='Ryan Northey',
    maintainer_email='ryan@synca.io',
    license='Apache Software License 2.0',
    url='https://github.com/phlax/pytooling/abstracts',
    description='Abstract class and interface definitions',
    long_description=read('README.rst'),
    long_description_content_type='text/x-rst',
    py_modules=['abstracts'],
    packages=find_namespace_packages(),
    package_data={'abstracts': ['py.typed']},
    python_requires='>=3.5',
    extras_require={
        "test": [
            "pytest",
            "pytest-asyncio",
            "pytest-coverage",
            "pytest-patches"],
        "lint": ['flake8'],
        "types": ['mypy'],
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
