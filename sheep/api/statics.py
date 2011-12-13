#!/usr/bin/python
# encoding: UTF-8

"""
static_files url replace
"""

import os

__all__ = ['static_files']

def static_files(path, expire=900):
    if os.environ.get('SHEEP_STATICS'):
        key = os.environ['SHEEP_STATIC_KEY']
        upt = make_upt(key, path, expire)
        return os.environ['SHEEP_STATICS'] + path + '?_upt=' + upt
    return path

def make_upt(key, path, expire=900):
    import time
    import hashlib
    e = time.time() + expire
    s = key + '&' + str(e) + '&' + path
    m = hashlib.md5()
    m.update(s)
    s = m.hexdigest()[12:20]
    return s + str(e)
