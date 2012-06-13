#!/usr/bin/python
# encoding: UTF-8

import os
import time
import signal
import threading

from sheep.setup import activate_app

debug = True
loglevel = 'debug'
accesslog = '-'
access_log_format = """%(t)s "%(r)s" %(s)s %(b)s %(HTTP_X_SHEEP_REQUEST_TIME_IN_MS)sms"""

def post_fork(server, workers):
    activate_app(os.environ['SHEEP_APPROOT'])

class Reloader(threading.Thread):
    """Auto reloader for auto-reloading gunicorn workers when .py file modified
    """

    def __init__(self, server):
        self.server = server
        threading.Thread.__init__(self)
        self.setDaemon(True)

    def run(self):
        monitor_dirs = [os.environ['SHEEP_APPROOT']] + os.environ.get('SHEEP_RELOAD_MONITOR_DIRS', '').split(':')
        modify_times = gen_files(monitor_dirs)

        while os.getpid() == self.server.pid:   # do not monitor in worker processes
            #start = time.time()
            new_modify_times = gen_files(monitor_dirs)
            diff = set(new_modify_times.items()).symmetric_difference(modify_times.items())
            if diff:
                print '%s modified' %  ', '.join(set(f for f, t in diff))
                os.kill(self.server.pid, signal.SIGHUP)

            modify_times = new_modify_times
            time.sleep(2)

def gen_files(monitor_dirs):
    modify_times = {}
    for monitor_dir in monitor_dirs:
        for root, dirs, files in os.walk(monitor_dir):
            if '/.svn' in root:
                continue
            for _file in (os.path.join(root, name) for name in files):
                if _file.endswith('.py') or _file.endswith('.ptl') \
                        or _file.endswith('.yaml'):
                    modify_times[_file] = os.stat(_file).st_mtime
    return modify_times

def when_ready(server):
    """Gunicorn server ready hook
    """

    Reloader(server).start()

if 'SHEEP_APPROOT' in os.environ:
    local_config_path = os.path.join(os.environ['SHEEP_APPROOT'],
                                     'local_appserver_config.py')
    if os.path.exists(local_config_path):
        namespace = {}
        try:
            execfile(local_config_path, namespace)
        except Exception:
            pass
        else:
            globals().update(namespace)
