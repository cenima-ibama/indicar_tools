#!/usr/bin/env python

# Indicar Landsat Geoprocessing Tools
#
#
# Author: Hex Gis
# Contributor: willemarcel
#
# License: GPLv3

from __future__ import print_function
import sys
import subprocess

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

# Check if gdal-config is installed
if subprocess.call(['which', 'gdal-config']):
    error = """Error: gdal-config is not installed on this machine.
This installation requires gdal-config to proceed.

If you are on Mac OSX, you can installed gdal-config by running:
    brew install gdal

On Ubuntu you should run:
    sudo apt-get install libgdal1-dev

Exiting the setup now!"""
    print(error)

    sys.exit(1)


def readme():
    with open("README.md") as f:
        return f.read()

setup(name="indicar",
      version='0.7.0',
      description="indicar-tools is the software made by the Indicar Project" +
      " to process Landsat imagery.",
      long_description=readme(),
      author="willemarcel",
      author_email="wille.marcel@hexgis.com",
      scripts=["bin/indicar"],
      url="https://github.com/ibamacsr/indicar-tools",
      packages=["indicar"],
      include_package_data=True,
      license="GPLv3",
      platforms="Posix; MacOS X",
      install_requires=[
          "GDAL>=1.9.0",
          "numpy==1.9.1"
      ],
      extras_require={
          'test': ['pytest'],
      },
      )
