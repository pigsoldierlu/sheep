#!/usr/bin/python
# encoding: UTF-8

import os
import sys
from websocket import create_connection
from .util import find_app_root, load_app_config

def populate_argument_parser(parser):
    parser.add_argument('root_path', metavar="<app root>", nargs='?',
                        help="directory contains app.yaml "
                        "[default: find automatically in parent dirs]")

def main(args):
    root_path = args.root_path or find_app_root()
    appcfg = load_app_config(root_path)
    appname = appcfg['application']
    try:
        ws = create_connection("ws://%s.dapps.douban.com:7302/_dae/log/" % appname)
    except:
        print 'Can\'t connect remote.'
        return
    line = ''
    log_type = ''
    try:
        while True:
            lines = ws.recv()
            if not lines:
                continue
            for line in lines.split('\n'):
                line += '\n'
                if line.startswith('==>'):
                    sys.stdout.write(line)
                    if line.find('dae_accesslog') != -1:
                        log_type = 'ACCESSLOG'
                    if line.find('dae_applog') != -1:
                        log_type = 'APPLOG'
                    continue
                if line.startswith('tail') or line == '\r\n' or line == '\n':
                    sys.stdout.write(line)
                    continue
                if log_type == 'APPLOG':
                    sys.stdout.write(' '.join(line.split(' ', 2)[2:]))
                elif log_type == 'ACCESSLOG':
                    line = line.split(' ', 5)
                    sys.stdout.write(' '.join(line))
    except KeyboardInterrupt:
        ws.send('quit')
    except:
        import traceback
        traceback.print_exc()
