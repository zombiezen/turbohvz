#!/usr/bin/env python
#
#   setup.py
#   TurboHvZ
#
#   Copyright (C) 2008 Ross Light
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
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
        "SQLAlchemy>=0.4.2",
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

