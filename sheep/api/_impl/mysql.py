#!/usr/local/bin/python2.7
#coding:utf-8

import os
from farm.mysql import load_mysql_config

def get_mysql_conn_params():
    appname = os.environ.get('SHEEP_APPNAME')
    if not appname:
        return {}
    return load_mysql_config(appname)
