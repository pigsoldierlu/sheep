#!/usr/bin/python
# encoding: UTF-8

import os, sys

from sheep.env import init_app
from sheep.util import load_app_config, find_app_root
from sheep.app import SHEEPApplication

def populate_argument_parser(parser):
    parser.add_argument('approot', metavar="<app root>", nargs='?',
                        help="directory contains app.yaml "
                        "[default: find automatically in parent dirs]")
    parser.add_argument('-p', '--port', type=int, default=8080,
                        help="port for the server to run on [default: 8080]")
    parser.add_argument('--pidfile', help="file path to put pid in")
    parser.add_argument('--daemon', action='store_true', default=False,
                        help="daemonize the server process [default: false]")

def main(args):
    approot = os.path.abspath(args.approot or find_app_root())
    init_app(approot)
    return run_server(approot, args.port, args.pidfile, args.daemon)

def run_server(approot, port=8080, pidfile=None, daemon=False):
    appconf = load_app_config(approot)

    sys.argv = ['sheep serve', '-b', '0.0.0.0:{0}'.format(port)]

    if pidfile:
        sys.argv += ['-p', pidfile]

    if daemon:
        sys.argv += ['-D']

    sys.argv += ['-c', os.path.join(os.path.dirname(__file__),
                                   'dev_appserver_config.py')]
    worker = appconf.get('worker', 'async')
    if worker == 'async':
        worker = 'sheep.gworkers.ggevent.GeventWorker'
    sys.argv += ['-k', worker]

    nworkers = appconf.get('nworkers', '1')
    sys.argv += ['-w', str(nworkers)]

    sys.argv.append(approot)  # must be the only positional parameter

    def add_handler(app):
        dev_handler = {'url': '/_sheep/.*', 'wsgi_app': 'sheep.dev:dispatcher'}
        app.appconf['handlers'].insert(0, dev_handler)

    app = SHEEPApplication(on_init=add_handler)
    return app.run()

