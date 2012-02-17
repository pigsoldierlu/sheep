#!/usr/bin/python
# encoding: UTF-8

"""Monkey patches for various module."""

from .util import load_dev_config, load_app_config

def patch_MySQLdb(approot):
    devcfg = load_dev_config(approot)
    if 'mysql' not in devcfg:
        return

    import MySQLdb
    if getattr(MySQLdb, 'sheep_patched', False):
        return

    origin_connect = MySQLdb.connect
    mysql_cfg = devcfg['mysql']

    def connect(host='sheep', **kwargs):
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
    if appcfg.get('worker', 'gevent') == 'gevent':
        patch_subprocess()
