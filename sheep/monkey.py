#!/usr/bin/python
# encoding: UTF-8

"""Monkey patches for various module."""

import os
from .util import load_dev_config

def use_pymysql():
    try:
        from pymysql import install_as_MySQLdb
    except ImportError:
        pass
    else:
        install_as_MySQLdb()

def patch_MySQLdb(approot):
    use_pymysql()
    devcfg = load_dev_config(approot)

    import MySQLdb
    if getattr(MySQLdb, 'sheep_patched', False):
        return

    origin_connect = MySQLdb.connect
    if not devcfg:
        mysql_cfg = {}
    else:
        mysql_cfg = devcfg.get('mysql', {})

    def connect(host='sheep', **kwargs):
        kwargs.setdefault('use_unicode', False)
        kwargs.setdefault('charset', 'utf8')
        if host == 'sheep':
            kw = kwargs.copy()
            kw.update(mysql_cfg)
            return origin_connect(**kw)
        else:
            return origin_connect(host=host, **kwargs)

    MySQLdb.connect = connect
    MySQLdb.sheep_patched = True

def patch_subprocess():
    """Only needed for async workers"""

    import subprocess
    subprocess.OLDPIPE = subprocess.PIPE
    subprocess.OLDPopen = subprocess.Popen

    from sheep.libs.subprocess import Popen, PIPE
    if getattr(subprocess, 'sheep_patched', False):
        return

    subprocess.PIPE = PIPE
    subprocess.Popen = Popen
    setattr(subprocess, 'sheep_patched', '')

def patch_logging():
    """Only needed for async workers"""

    import logging
    from gevent.coros import RLock
    logging._lock = RLock()

def patch_all(approot):
    if os.environ['SHEEP_WORKER'] == 'async':
        import gevent.monkey
        gevent.monkey.patch_all()
        patch_subprocess()
        patch_logging()

    patch_MySQLdb(approot)

