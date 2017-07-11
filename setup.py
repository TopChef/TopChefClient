#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name='topchef_client',
    version='0.2',
    description='Python library for interfacing with the TopChef server',
    author='Michal Kononenko',
    author_email='mkononen@uwaterloo.ca',
    packages=find_packages(exclude=["*.tests.*"]),
    install_requires=[
        'six==1.10.0',
        'requests==2.11.1'
    ]
)
