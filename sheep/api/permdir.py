#!/usr/bin/python
# encoding: UTF-8

"""API for permanent dir.

Public module variables:

permdir -- a string containing path to the directory holding permanent files.
"""

__all__ = ['permdir']

import os
from sheep.util import find_app_root

approot = os.environ.get('SHEEP_APPROOT') or find_app_root(raises=False) or ''
permdir = os.path.join(approot, 'permdir')
