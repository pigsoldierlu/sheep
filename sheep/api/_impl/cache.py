#!/usr/local/bin/python2.7
#coding:utf-8

from werkzeug.contrib import cache as _cache

backend = _cache.FileSystemCache('/tmp/sheep')
