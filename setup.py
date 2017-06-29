#!/usr/bin/env python
from setuptools import setup

setup(
    name='topchef_client',
    version='0.1',
    description='Python library for interfacing with the TopChef server',
    author='Michal Kononenko',
    author_email='mkononen@uwaterloo.ca',
    packages=['topchef_client'],
    install_requires=[
        'six==1.10.0',
        'requests==2.11.1'
    ]
)
