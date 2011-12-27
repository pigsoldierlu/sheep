#!/usr/bin/python
# encoding: UTF-8

import os, sys

from .util import load_app_config, activate_virtualenv, find_app_root, \
        load_dev_config
from .appserver import SHEEPApplication
from .monkey import patch_all

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
    appconf = load_app_config(root_path)
    cmd = ['sheep-gunicorn', '-b', ':{0}'.format(port)]

    if pidfile:
        cmd += ['-p', pidfile]

    if daemon:
        cmd += ['-D']

    cmd += ['-c', os.path.join(os.path.dirname(__file__),
                               'dev_appserver_config.py'),
            '-k', appconf.get('worker', 'gevent'),
           ]
    cmd.append(root_path)
    os.environ['SHEEP_APPROOT'] = root_path
    os.environ['SHEEP_RELOAD_MONITOR_DIRS'] = root_path
    if 'PYTHONPATH' not in os.environ:
        os.environ['PYTHONPATH'] = root_path
    else:
        os.environ['PYTHONPATH'] = root_path + ':' + os.environ['PYTHONPATH']

    os.chdir(root_path)

    # run gunicorn_run() on exec'ed process
    os.execvp('sheep-gunicorn', cmd)

def gunicorn_run():
    try:
        from pymysql import install_as_MySQLdb
    except ImportError:
        pass
    else:
        install_as_MySQLdb()

    app = SHEEPApplication()
    sys.path.insert(0, app.root_path)
    activate_virtualenv(app.root_path)
    import logging
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('gunicorn').propagate = False
    patch_all(app.root_path)
    return app.run()


