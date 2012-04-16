#!/usr/bin/python
# encoding: UTF-8

"""Monkey patches for various module."""

from .util import load_dev_config, load_app_config

def use_pymysql():
    try:
        import sys
        from pymysql import converters
        from pymysql import install_as_MySQLdb
        from pymysql.connections import Connection
        from pymysql.converters import escape_string

        if not getattr(converters, 'Thing2Literal', None):
            def Thing2Literal(o, d):
                return "'%s'" % escape_string(str(o))
            setattr(converters, 'Thing2Literal', Thing2Literal)
            sys.modules['MySQLdb.converters'] = sys.modules['pymysql.converters']

        if not getattr(Connection, 'select_db', None):
            def select_db(self, db):
                self.db = db
                self.query("USE %s" % db)
            setattr(Connection, 'select_db', select_db)
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

