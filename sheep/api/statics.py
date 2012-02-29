#!/usr/bin/python
# encoding: UTF-8

"""
static_files url replace
"""
__all__ = ['static_files', 'public_files', 'upload_files']

import os
from sheep.util import load_app_config

approot = os.environ.get('SHEEP_APPROOT') or find_app_root(raises=False) or ''
appconf = load_app_config(approot)

appname = appconf['application']
upload_prefix = appconf['upload_prefix']
public_prefix = appconf['public_prefix']

static_files = lambda path: path

def upload_files(path):
    return os.path.join(upload_prefix, appname) + path

def public_files(path):
    return public_prefix + path