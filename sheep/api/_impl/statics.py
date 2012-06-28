#!/usr/bin/python
# encoding: UTF-8

"""
static_files url replace
"""
__all__ = ['static_files', 'public_files', 'upload_files']

import os
from sheep.util import load_app_config, find_app_root

approot = os.environ.get('SHEEP_APPROOT') or find_app_root(raises=False) or ''
appconf = load_app_config(approot)

appname = appconf['application']
upload_prefix = appconf.get('upload_prefix', '')
public_prefix = appconf.get('public_prefix', '')

static_files = lambda path: path
upload_files = lambda path: os.path.join(upload_prefix, appname) + path
public_files = lambda path: public_prefix + path
