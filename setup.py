#!/usr/bin/env python

import os
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="python-omgeo",
    version="6.0.3",
    description="Geocoding Library using ESRI, Google, Bing Maps, US Census, OpenStreetMap, Pelias, and MapQuest geocoders",
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
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 3'
    ],
    dependency_links=[],
    install_requires=[
        'requests >= 2.18',
    ],
    test_suite='omgeo.tests.tests',
)
