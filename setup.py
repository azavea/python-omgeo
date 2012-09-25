#!/usr/bin/env python

import os
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name="python-omgeo",
    version="1.5.3",
    description="Geocoding Library using ESRI, Bing Maps, and MapQuest geocoders",
    author="Azavea, Inc.",
    author_email="info@azavea.com",
    url="http://github.com/azavea/python-omgeo",
    license="MIT",
    long_description=read('README.rst'),
    packages=find_packages(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Topic :: Scientific/Engineering :: GIS',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 2.6'
    ],
    dependency_links=['http://github.com/htj/suds-htj/tarball/master#suds=0.4.1-htj'],
    install_requires=['suds>=0.4'], 
    test_suite='omgeo.tests.tests',
)
