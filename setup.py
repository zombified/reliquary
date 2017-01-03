# This file is part of Reliquary.
#
# Reliquary is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

requires = [
    'Paste',
    'pyramid',
    'pyramid_chameleon',
    'pyramid_debugtoolbar',
    'pyramid_tm',
    'requests',
    'sqlalchemy',
    'waitress',
    'zope.sqlalchemy',
    ]

tests_require = [
    'WebTest >= 1.3.1',  # py3 compat
    'pytest',  # includes virtualenv
    'pytest-cov',
    ]

setup(name='reliquary',
      version='0.1.0',
      description='reliquary',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
          "Development Status :: 2 - Pre-Alpha",
          "Environment :: Web Environment",
          "Intended Audience :: Developers",
          "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
          "Programming Language :: Python",
          "Programming Language :: Python :: 3.5",
          "Topic :: Internet :: Proxy Servers",
          "Topic :: Internet :: WWW/HTTP",
      ],
      author='Joel Kleier',
      author_email='joel@kleier.us',
      url='https://github.com/zombified/reliquary',
      keywords='web pyramid pylons',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      extras_require={
          'testing': tests_require,
      },
      install_requires=requires,
      entry_points={
          "paste.app_factory": [
              "main = reliquary:main"
          ],
          "console_scripts": [
              "init_reliquary = reliquary.scripts:init_reliquary",
              "reindex_reliquary = reliquary.scripts:reindex",
          ],
      })
