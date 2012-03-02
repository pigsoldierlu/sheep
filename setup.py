#!/usr/bin/python
# encoding: UTF-8

from setuptools import setup, find_packages
import sys, os

version = '0.1'
install_requires = [
    'virtualenv>=1.5',
    'PyYAML',
    'gunicorn>=0.13',
    'PyMySQL',
    'PasteDeploy>=1.3.3',
    'PasteScript>=1.7.3',
    'Mako',
    'gevent',
    'mercurial',
]
if sys.version_info < (2, 7):
    install_requires.append('argparse')

setup(name='sheep',
      version=version,
      description="Sheep SDK",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='ZheFu Peng',
      author_email='ilskdw@gmail.com',
      url='http://cmgs.me',
      license='',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=install_requires,
      entry_points="""
      [console_scripts]
      sheep = sheep.commands:main
      sheep-gunicorn = sheep.dev_appserver:gunicorn_run

      [paste.paster_create_template]
      sheep = sheep.templates:SHEEPTemplate
      """,
      )
