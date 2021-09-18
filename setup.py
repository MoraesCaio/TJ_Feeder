#!/usr/bin/env python

import setuptools


setuptools.setup(
    name='tj_feeder',
    version='0.0.1',
    description='Tool to generate daily input for Task Juggler',
    author='Caio Moraes',
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': [
            'tj_feed=tj_feeder.tj_feed:main',
        ],
    },
    url='',
)