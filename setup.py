# coding: utf-8
# python setup.py sdist register upload
from distutils.core import setup

setup(
    name='park-worker-p2',
    version='0.1.0',
    description='Workers for park-keeper project for python version 2.',
    author='Telminov Sergey',
    url='https://github.com/telminov/park-worker-p2',
    packages=[
        'parkworker2',
        'parkworker2/bin',
        'parkworker2/monits',
    ],
    license='The MIT License',
    install_requires=[
        'park-worker-base', 'pyzmq', 'pytz', 'ansible', 'sw-python-utils'
    ],
)
