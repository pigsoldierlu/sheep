#!/usr/bin/python
# encoding: UTF-8

import sys
from threading import Thread
from websocket import create_connection
from sheep.util import find_app_root, load_app_config, load_dev_config
from subprocess import call
import logging

logger = logging.getLogger(__name__)

def populate_argument_parser(parser):
    parser.add_argument('root_path', metavar='<app root>', nargs='?',
                      help="directory contains app.yaml "
                           "[default: find automatically in parent dirs]")
    parser.add_argument('--remote', action='store_true',
            help="connect to the database in production environment (DANGEROURS!)")

def read_output(ws):
    while True:
        try:
            ret = ws.recv()
            sys.stdout.write(ret)
            sys.stdout.flush()
        except:
            break
    ws.close()

def main(args):
    if args.remote:
        return remote_main(args)
    else:
        return dev_main(args)

def dev_main(args):
    root_path = args.root_path or find_app_root()
    devcfg = load_dev_config(root_path)
    if 'mysql' not in devcfg:
        logger.fatal("No mysql defined in dev.yaml")
        return 1

    cfg = devcfg['mysql']

    cmd = ['mysql']
    if 'host' in cfg:
        cmd += ['-h', cfg['host']]
    if 'port' in cfg:
        cmd += ['-P', str(cfg['port'])]
    if 'user' in cfg:
        cmd += ['-u', cfg['user']]
    if 'passwd' in cfg:
        cmd += ['-p%s' % cfg['passwd']]
    cmd += [cfg['db']]

    return call(cmd)

def remote_main(args):
    logger.warning("CAUTION! CAUTION! CAUTION! ")
    logger.warning("You are connecting to the database in production environment!")
    logger.warning("BE CAREFUL!")

    root_path = args.root_path or find_app_root()
    appcfg = load_app_config(root_path)
    appname = appcfg['application']
    try:
        ws = create_connection("ws://%s.xiaom.co:5000/_sheep/mysql/" % appname)
        read_thread = Thread(target=read_output, args=(ws, ))
        read_thread.start()
    except:
        print 'Can\'t connect remote.'
        return
    try:
        while True:
            if not ws.connected:
                break
            else:
                command = raw_input('')
                if not command.endswith('\n'):
                    command += '\n'
                ws.send(command)
                if command == 'quit\n' or command == '\\q\n':
                    sys.stdout.write('Wait for connection closed.\t\n')
                    read_thread.join()
    except:
        ws.send('quit\n')
        read_thread.join()
    finally:
        ws.close()
