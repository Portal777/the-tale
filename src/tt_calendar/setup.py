
import re
import json
import setuptools

VERSION = '0.1'

setuptools.setup(
    name='TTCalendar',
    version=VERSION,
    description='Calendar library for The Tale',
    long_description = 'Calendar library for The Tale',
    url='https://github.com/Tiendil/the-tale',
    author='Aleksey Yeletsky <Tiendil>',
    author_email='a.eletsky@gmail.com',
    license='BSD',
    packages=setuptools.find_packages(),
    install_requires=[],
    include_package_data=True,
    test_suite = 'tests' )
