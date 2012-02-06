#!/usr/local/bin/python2.7
#coding:utf-8

from werkzeug.contrib.sessions import *

origin_session_middleware = SessionMiddleware.__init__
def init(self, app, store, **kwargs):
    kw = kwargs.copy()
    kw.update(cookie_name='xid', \
              environ_key='xiaomen.session')
    return origin_session_middleware(self, app, store, **kw)
SessionMiddleware.__init__ = init
