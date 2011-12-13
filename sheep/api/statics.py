#!/usr/bin/python
# encoding: UTF-8

"""
static_files url replace
"""

import os

__all__ = ['static_files']

def static_files(path):
    if os.environ.get('SHEEP_STATICS'):
        appname = os.environ['SHEEP_APPNAME']
        return os.path.join(os.environ['SHEEP_STATICS'], appname, path)
    return path
