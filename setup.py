#!/usr/bin/env python
#
#   setup.py
#   HvZ
#

import os

from setuptools import setup, find_packages
from turbogears.finddata import find_package_data

__author__ = 'Ross Light'
__date__ = 'March 30, 2008'

execfile(os.path.join("hvz", "release.py"))

packages = find_packages()
package_data = find_package_data(where='hvz', package='hvz')
if os.path.isdir('locales'):
    packages.append('locales')
    package_data.update(find_package_data(where='locales', exclude=('*.po',),
                                          only_in_packages=False))

setup(
    name="TurboHvZ",
    version=version,
    description=description,
    author=author,
    author_email=email,
    url=url,
    download_url=download_url,
    license=license,
    install_requires=[
        "TurboGears >= 1.0.4.4",
        "Genshi >= 0.4.4",
        "SQLAlchemy>=0.3.10",
        "Elixir>=0.4.0",
        "pytz",
    ],
    zip_safe=False,
    packages=packages,
    package_data=package_data,
    keywords=[
        'turbogears.app',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Framework :: TurboGears',
        'Framework :: TurboGears :: Applications',
    ],
    test_suite='nose.collector',
    entry_points={
        'console_scripts': [
            'start-turbohvz = hvz.commands:start',
            'turbohvz-create-perms = hvz.commands:create_permissions',
            'turbohvz-create-admin = hvz.commands:create_admin',
        ],
    },
    data_files=[('config', ['default.cfg'])],
)

