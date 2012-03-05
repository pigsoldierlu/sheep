import logging

from sheep.app import WSGIApplication
from sheep.util import load_app_config
from gunicorn.app.base import Application

class MixedGunicornApplication(Application):
    def __init__(self, usage=None, on_init=None):
        self.on_init = on_init
        super(MixedGunicornApplication, self).__init__(usage=usage)

    def init(self, parser, opts, args):
        if len(args) != 1:
            parser.error("No application root specified.")

        self.root_path = args[0]
        self.appconf = load_app_config(self.root_path)
        if callable(self.on_init):
            self.on_init(self)

    def load(self):
        return MixedApplication(self.appconf)


class MixedApplication(object):
    def __init__(self, appcfg):
        self.appcfg = appcfg
        self.wsgiapp = WSGIApplication(appcfg)

    def __call__(self, environ, start_response):
            return self.wsgiapp(environ, start_response)

