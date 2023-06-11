#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('VERSION') as version:
    version = version.read()

with open('REQUIREMENTS') as requirements:
    requirements = requirements.read()

setup(
    author="Issaku Kawashima",
    author_email='issakuss@gmail.com',
    python_requires='>=3.10',
    description="Academic paper management with Notion",
    entry_points={
        'console_scripts': [
            'papnt=papnt.cli:main',
        ],
    },
    install_requires=requirements,
    include_package_data=True,
    keywords='papnt',
    name='papnt',
    packages=find_packages(include=['papnt', 'papnt.*']),
    url='https://github.com/issakuss/papnt',
    version=version,
    zip_safe=False,
)
