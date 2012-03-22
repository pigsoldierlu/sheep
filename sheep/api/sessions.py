#!/usr/local/bin/python2.7
#coding:utf-8

from werkzeug.contrib import sessions
from werkzeug.contrib.sessions import *

from werkzeug.wsgi import ClosingIterator
from werkzeug.utils import dump_cookie, parse_cookie

class SessionMiddleware(sessions.SessionMiddleware):
    def __init__(self, app, store, **kwargs):
        kw = kwargs.copy()
        kw.update(cookie_name='xid', \
                  environ_key='xiaomen.session')
        sessions.SessionMiddleware.__init__(self, app, store, **kw)

    def __call__(self, environ, start_response):
        cookie = parse_cookie(environ.get('HTTP_COOKIE', ''))
        sid = cookie.get(self.cookie_name, None)
        if sid is None:
            session = self.store.new()
        else:
            session = self.store.get(sid)
        environ[self.environ_key] = session

        def injecting_start_response(status, headers, exc_info=None):
            if session.should_save:
                age = session.get('_sheep_permstore', self.cookie_age)
                try:
                    age = int(age)
                except:
                    age = self.cookie_age
                self.store.save(session)
                headers.append(('Set-Cookie', dump_cookie(self.cookie_name,
                                session.sid, age,
                                self.cookie_expires, self.cookie_path,
                                self.cookie_domain, self.cookie_secure,
                                self.cookie_httponly)))
            return start_response(status, headers, exc_info)
        return ClosingIterator(self.app(environ, injecting_start_response),
                               lambda: self.store.save_if_modified(session))

