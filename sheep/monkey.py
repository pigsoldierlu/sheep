#!/usr/bin/python
# encoding: UTF-8

"""Monkey patches for various module."""

from .util import load_dev_config, load_app_config

def patch_MySQLdb(approot):
    try:
        from pymysql import install_as_MySQLdb
    except ImportError:
        pass
    else:
        install_as_MySQLdb()

    devcfg = load_dev_config(approot)
    import MySQLdb
    if getattr(MySQLdb, 'sheep_patched', False):
        return

    origin_connect = MySQLdb.connect
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
    import subprocess
    from libs.subprocess import Popen, PIPE
    if getattr(subprocess, 'sheep_patched', False):
        return

    subprocess.PIPE = PIPE
    subprocess.Popen = Popen
    setattr(subprocess, 'sheep_patched', '')


def patch_all(approot):
    appcfg = load_app_config(approot)
    patch_MySQLdb(approot)

