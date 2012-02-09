#!/usr/bin/python
# encoding: UTF-8

import os
import re
import time
import logging
import tempfile
import mimetypes
import gevent_profiler

from gunicorn.app.base import Application
from gunicorn import util

from .util import load_app_config

logger = logging.getLogger()
gevent_profiler.set_summary_output(None)

class Error(Exception):
    """Base-class for exceptions in this module."""

class InvalidAppConfigError(Error):
    """This supplied application configuration file is invalid."""


class SHEEPApplication(Application):
    def init(self, parser, opts, args):
        if len(args) != 1:
            parser.error("No application root specified.")

        self.root_path = args[0]
        self.appconf = load_app_config(self.root_path)
        self.handlers = None

    def load(self):
        return self

    def profile_call(self, handler, environ, start_response):
        stats = tempfile.NamedTemporaryFile(delete=True)
        trace = tempfile.NamedTemporaryFile(delete=True)
        gevent_profiler.set_stats_output(stats.name)
        gevent_profiler.set_trace_output(trace.name)
        def sr(status, headers, exc_info):
            new_headers = []
            for h in headers:
                if h[0] == 'Content-Length':
                    continue
                new_headers.append(h)
            start_response(status, new_headers, exc_info)

        gevent_profiler.attach()
        for line in handler(environ, sr):
            yield line
        gevent_profiler.detach()
        yield '<pre>'
        for line in open(stats.name, 'r').xreadlines():
            yield line
        for line in open(trace.name, 'r').xreadlines():
            yield line
        yield '</pre>'
        stats.close()
        trace.close()

    def __call__(self, environ, start_response):
        try:
            path_info = environ['PATH_INFO'] or '/'
            environ['sheep.config'] = self.appconf
            if self.handlers is None:
                self.handlers = []
                for h in self.appconf['handlers']:
                    try:
                        app_handler = handler_factory(h)
                        self.handlers.append(app_handler)
                    except:
                        continue

            for handler in self.handlers:
                m = handler.match(path_info)
                if m:
                    environ['sheep.matched'] = m
                    if environ['QUERY_STRING'] and \
                            '_sheep_profile=1' in environ['QUERY_STRING']:
                        return self.profile_call(handler, environ, start_response)
                    return handler(environ, start_response)
        except:
            logger.exception("error occurred when handle request")
            raise

        start_response('404 Not Found', [])
        return ["404 Not Found"]

def handler_factory(config):
    mapping = [('wsgi_app', WSGIAppHandler),
               ('static_files', StaticFilesHandler),
               ('paste', PasteHandler),
              ]
    for handler_type, cls in mapping:
        if handler_type in config:
            try:
                return cls(config)
            except Exception:
                logger.exception("load handler failed")
                raise
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

class WSGIAppHandler(BaseHandler, WholeMatchMixIn):
    def make_app(self, config):
        return util.import_app(config['wsgi_app'])

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
        path = self.path
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



