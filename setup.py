#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read().replace('.. :changelog:', '')

with open('requirements.txt') as requirements_file:
    requirements = requirements_file.read().splitlines()

test_requirements = [
]

setup(
    name='zeroservices',
    version='0.1.0',
    description="Network services made easy and Micro-Services architectures made fucking easy.",
    long_description=readme + '\n\n' + history,
    author="Boris Feld",
    author_email='lothiraldan@gmail.com',
    url='https://github.com/lothiraldan/zeroservices',
    packages=[
        'zeroservices', 'zeroservices.medium',
        'zeroservices.backend', 'zeroservices.services',
        'zeroservices.discovery'
    ],
    package_dir={'zeroservices':
                 'zeroservices'},
    include_package_data=True,
    install_requires=requirements,
    license="MIT",
    zip_safe=False,
    keywords='zeroservices',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
