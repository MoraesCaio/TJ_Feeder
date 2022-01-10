#!/usr/bin/env python
"""Install TJ Feeder module
"""


import setuptools

with open("README.md", "r") as description_file:
    long_description = description_file.read()


setuptools.setup(
    name="tj_feeder",
    version="0.1.0",
    description="Tool to generate daily input for Task Juggler",
    author="Caio Moraes",
    author_email="caiomoraes.cesar@gmail.com",
    long_description=long_description,
    long_description_content_type="text/markdown",
    # url='',
    packages=setuptools.find_packages(),
    install_requires=["fire==0.4.0", "loguru==0.5.3", "pandas==1.3.3"],
    entry_points={"console_scripts": ["tj_feed=tj_feeder.tj_feed:main"]},
    include_package_data=True,
    package_data={"": ["data/cfg.json"]},
    classifiers=[
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Development Status :: 5 - Production/Stable",
    ],
)
