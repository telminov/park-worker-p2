# coding: utf-8
from distutils.core import setup

setup(
    name='django-park-worker-p2',
    version='0.0.1',
    description='Workers for park-keeper project for python version 2.',
    author='Telminov Sergey',
    url='https://github.com/telminov/park-worker-p2',
    packages=['parkworker2',],
    license='The MIT License',
    install_requires=[
        'park-worker-base', 'pyzmq', 'pytz', 'ansible=1.9', 'sw-python-utils'
    ],
)
