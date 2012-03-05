#!/usr/bin/python
# encoding: UTF-8

import os, sys

from sheep.monkey import patch_all
from sheep.gworkers.mix import MixedGunicornApplication
from sheep.util import load_app_config, activate_virtualenv, find_app_root, \
        load_dev_config, init_sdk_environ

def populate_argument_parser(parser):
    parser.add_argument('root_path', metavar="<app root>", nargs='?',
                        help="directory contains app.yaml "
                        "[default: find automatically in parent dirs]")
    parser.add_argument('-p', '--port', type=int, default=8080,
                        help="port for the server to run on [default: 8080]")
    parser.add_argument('--pidfile', help="file path to put pid in")
    parser.add_argument('--daemon', action='store_true', default=False,
                        help="daemonize the server process [default: false]")

def main(args):
    root_path = os.path.abspath(args.root_path or find_app_root())
    return run_server(root_path, args.port, args.pidfile, args.daemon)

def run_server(root_path, port=8080, pidfile=None, daemon=False):
    init_sdk_environ(root_path)
    appconf = load_app_config(root_path)

    sys.argv = ['sheep serve', '-b', '0.0.0.0:{0}'.format(port)]

    if pidfile:
        sys.argv += ['-p', pidfile]

    if daemon:
        sys.argv += ['-D']

    sys.argv += ['-c', os.path.join(os.path.dirname(__file__),
                               'dev_appserver_config.py'),
            '-k', appconf.get('worker', 'sheep.gworkers.ggevent.GeventWorker'),
           ]
    sys.argv.append(root_path)

    def add_handler(app):
        dev_handler = {'url': '/_sheep/.*', 'wsgi_app': 'sheep.dev:dispatcher'}
        app.appconf['handlers'].insert(0, dev_handler)
    app = MixedGunicornApplication(on_init=add_handler)
    return app.run()

