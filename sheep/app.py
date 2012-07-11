#!/usr/bin/python
# encoding: UTF-8

import os
import re
import sys
import time
import types
import pstats
import logging
import cProfile
import tempfile
import mimetypes
from cStringIO import StringIO

from gunicorn.app.base import Application
from gunicorn import util

from .libs.websocket import WebSocketWSGI
from .util import load_app_config, set_environ

from sheep.api.sentry import report

logger = logging.getLogger()

PROFILE_LIMIT = 60
PROFILE_STYLE = ('background-color: #ff9; color: #000; '
                 'border: 2px solid #000; padding: 5px; '
                 "font-family: Courier, 'Courier New', monospace; "
                 "clear: both;")

class Error(Exception):
    """Base-class for exceptions in this module."""

class InvalidAppConfigError(Error):
    """This supplied application configuration file is invalid."""

class SHEEPApplication(Application):
    def __init__(self, usage=None, on_init=None):
        self.on_init = on_init
        super(SHEEPApplication, self).__init__(usage=usage)

    def init(self, parser, opts, args):
        if len(args) != 1:
            parser.error("No application root specified.")

        self.root_path = args[0]
        self.appconf = load_app_config(self.root_path)
        if callable(self.on_init):
            self.on_init(self)

    def load(self):
        return MixedApplication(self.appconf)

class MixedResult(object):
    def __init__(self, value):
        self._value = value

    def __iter__(self):
        return self

    def next(self):
        try:
            return self._value.next()
        except Exception:
            exc_type, exc_value, tb = sys.exc_info()
            logger.exception("error occurred when handle request")
            report()
            raise exc_type, exc_value, tb

class MixedApplication(object):
    def __init__(self, appcfg):
        self.appcfg = appcfg
        self.wsgiapp = WSGIApplication(appcfg)

    def __call__(self, environ, start_response):
        result = self.wsgiapp(environ, start_response)
        if isinstance(result, types.GeneratorType):
            return MixedResult(result)
        return result

class WSGIApplication(object):
    def __init__(self, appconf):
        self.appconf = appconf
        self.handlers = None

    def profile_call(self, handler, environ, start_response):
        stats_file = tempfile.NamedTemporaryFile(delete=True)
        output_io = StringIO()
        prof = cProfile.Profile()
        def sr(status, headers, exc_info=None):
            new_headers = []
            for h in headers:
                if h[0] == 'Content-Length':
                    continue
                new_headers.append(h)
            return start_response(status, new_headers, exc_info)

        ret = prof.runcall(lambda h, e, r:list(h(e, r)), handler, environ, sr)
        prof.dump_stats(stats_file.name)
        for line in ret:
            yield line
        p = pstats.Stats(stats_file.name, stream=output_io)
        p.sort_stats('time','calls')
        p.print_stats(PROFILE_LIMIT)
        p.print_callers(PROFILE_LIMIT)
        yield '<pre id="profile_log" style="%s">' % PROFILE_STYLE
        yield output_io.getvalue()
        yield '</pre>'
        stats_file.close()
        output_io.close()

    def __call__(self, environ, start_response):
        set_environ(environ)
        path_info = environ['PATH_INFO'] or '/'
        environ['sheep.config'] = self.appconf
        if self.handlers is None:
            self.handlers = []
            for h in self.appconf['handlers']:
                try:
                    app_handler = handler_factory(h)
                    self.handlers.append(app_handler)
                except Exception:
                    logger.exception("load handler failed")
                    app_handler = LoadErrorHandler(h)
                    app_handler.set_traceback(sys.exc_info())
                    self.handlers.append(app_handler)

        for handler in self.handlers:
            m = handler.match(path_info)
            if m:
                environ['sheep.matched'] = m
                if environ['QUERY_STRING'] and \
                        '_sheep_profile=1' in environ['QUERY_STRING']:
                    return self.profile_call(handler, environ, start_response)
                return handler(environ, start_response)

        start_response('404 Not Found', [])
        return ["404 Not Found"]

def handler_factory(config):
    mapping = [('wsgi_app', WSGIAppHandler),
               ('static_files', StaticFilesHandler),
               ('paste', PasteHandler),
               ('websocket', WebsocketAppHandler),
               # callable handler is for easier test case writting
               ('callable', CallableAppHandler),
              ]
    for handler_type, cls in mapping:
        if handler_type in config:
            return cls(config)

    raise InvalidAppConfigError("invalid handler type for %s" % config)

class BaseHandler(object):
    def __init__(self, config):
        self.config = config
        regex = self.make_url_regex(config)
        try:
            self.url_re = re.compile(regex)
        except re.error, e:
            raise InvalidAppConfigError('regex %s does not compile: %s' % (regex, e))

        self.app = self.make_app(config)

    def match(self, path_info):
        return self.url_re.match(path_info)

    def __call__(self, environ, start_response):
        return self.app(environ, start_response)

class WholeMatchMixIn(object):
    def make_url_regex(self, config):
        regex = config['url']
        if regex.startswith('^') or regex.endswith('$'):
            raise InvalidAppConfigError('regex starts with "^" or ends with "$"')
        return regex + '$'

class PrefixMatchMixIn(object):
    def make_url_regex(self, config):
        regex = config['url']
        if regex.startswith('^') or regex.endswith('$') or '(' in regex:
            raise InvalidAppConfigError('regex starts with "^" or ends with "$" or "(" in it')
        return regex + '.*'

class LoadErrorHandler(BaseHandler, WholeMatchMixIn):
    def set_traceback(self, traceback):
        self.traceback = traceback

    def make_app(self, config):
        def _(e, sr):
            exc_type, exc_value, tb = self.traceback
            raise exc_type, exc_value, tb
        return _

class CallableAppHandler(BaseHandler, WholeMatchMixIn):
    def make_app(self, config):
        return config['callable']

class WSGIAppHandler(BaseHandler, WholeMatchMixIn):
    def make_app(self, config):
        return util.import_app(config['wsgi_app'])

class WebsocketAppHandler(WSGIAppHandler):
    def make_app(self, config):
        handle = util.import_app(config['websocket'])
        app = WebSocketWSGI(handle)
        return app

class PasteHandler(WSGIAppHandler):
    def make_app(self, config):
        from paste.deploy import loadapp
        from paste.deploy.converters import asbool

        ini = devini = config['paste']
        if ':' in ini:
            ini, devini = ini.split(':', 1)

        if not asbool(os.environ.get('SHEEP_PRODUCTION')):
            ini = devini

        return loadapp('config:' + ini, relative_to=os.getcwd())


class StaticFilesHandler(BaseHandler, WholeMatchMixIn):
    def make_app(self, config):
        return StaticFilesApplication(config['static_files'])


class StaticFilesApplication(object):
    def __init__(self, path_template):
        self.path_template = path_template

    def __call__(self, environ, start_response):
        m = environ['sheep.matched']
        path = m.expand(self.path_template)
        return StaticFileApplication(path)(environ, start_response)


class StaticFileApplication(object):
    def __init__(self, path):
        self.path = path

    def _get_last_modified(self, path):
        return os.stat(path).st_mtime

    def _generate_last_modified_string(self, path):
        mtime = self._get_last_modified(path)
        return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(mtime))

    def _if_modified_since(self, path, timestr):
        try:
            t = time.mktime(time.strptime(timestr, "%a, %d %b %Y %H:%M:%S GMT"))
        except ValueError:
            return True
        else:
            t -= time.timezone  # convert gmt to local time
            mtime = self._get_last_modified(path)
            return mtime > t

    def __call__(self, environ, start_response):
        path = os.path.join(os.environ['SHEEP_APPROOT'], self.path)
        if os.path.isfile(path):
            mimetype = mimetypes.guess_type(path)[0] or 'text/plain'
            last_modified = self._generate_last_modified_string(path)
            headers = [
                ('Content-type', mimetype),
                ('Last-Modified', last_modified),
            ]

            ims = environ.get('HTTP_IF_MODIFIED_SINCE')
            if ims and not self._if_modified_since(path, ims):
                start_response('304 Not Modified', headers)
                return ''

            start_response('200 OK', headers)
            return open(path)
        else:
            start_response('404 Not Found', [])
            return ['File not found']



