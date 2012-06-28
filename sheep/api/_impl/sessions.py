#!/usr/local/bin/python2.7
#coding:utf-8

from werkzeug.contrib import sessions

def init(self, app, store, **kwargs):
    kw = kwargs.copy()
    kw.update(cookie_name='xid', \
              environ_key='xiaomen.session')
    sessions.SessionMiddleware.__init__(self, app, store, **kw)

