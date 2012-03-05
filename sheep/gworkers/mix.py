import logging

from sheep.app import WSGIApplication
from sheep.util import load_app_config
from gunicorn.app.base import Application

class MixedGunicornApplication(Application):
    def init(self, parser, opts, args):
        if len(args) != 1:
            parser.error("No application root specified.")

        self.root_path = args[0]
        self.appconf = load_app_config(self.root_path)

    def load(self):
        return MixedApplication(self.appconf)


class MixedApplication(object):
    def __init__(self, appcfg):
        self.appcfg = appcfg
        self.wsgiapp = WSGIApplication(appcfg)

    def __call__(self, environ, start_response):
            return self.wsgiapp(environ, start_response)

