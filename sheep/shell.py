#!/opt/local/bin/python2.7
#coding:utf-8

import sys
from threading import Thread
from websocket import create_connection
from .util import find_app_root, load_app_config

def populate_argument_parser(parser):
    parser.add_argument('root_path', metavar='<app root>', nargs='?',
                      help="directory contains app.yaml "
                           "[default: find automatically in parent dirs]")
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
    root_path = args.root_path or find_app_root()
    appcfg = load_app_config(root_path)
    appname = appcfg['application']
    try:
        ws = create_connection("ws://%s.dapps.douban.com:7302/_dae/shell/" % appname)
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
                try:
                    command = raw_input('')
                    if not command.endswith('\n'):
                        command += '\n'
                    ws.send(command)
                    if command == 'quit()\n' or command == 'exit()\n':
                        sys.stdout.write('Wait for connection closed.\t\n')
                        read_thread.join()
                except KeyboardInterrupt:
                    print
                    print 'KeyboardInterrupt'
                    ws.send('\n')
    except:
        ws.send('quit()\n')
        read_thread.join()
    finally:
        ws.close()
