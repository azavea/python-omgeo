#!/usr/bin/env python

import sys
import os
import subprocess
from setuptools import setup, find_packages, Command

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

class RunTests(Command):
    description = "Run the unit test suite for python-omgeo."
    user_options = []
    extra_env = {}
    extra_args = []

    def run(self):
        run_tests_script_path = os.path.join(os.path.dirname(__file__), 'omgeo', 'run_tests.py')
        sys.exit(subprocess.call([run_tests_script_path]))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

setup(
    name="python-omgeo",
    version="1.3",
    description="A Python Geocoding Library",
    author="Azavea, Inc.",
    author_email="info@azavea.com",
    url="http://github.com/azavea/python-omgeo",
    license="MIT",
    long_description=read('README.rst'),
    cmdclass = { 'test': RunTests },
    packages=find_packages(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Topic :: Scientific/Engineering :: GIS',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 2.6'
    ],
    install_requires=[
        'suds==0.4'
    ]
)
