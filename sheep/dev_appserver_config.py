#!/usr/bin/python
# encoding: UTF-8

""" Gunicorn configs and hooks for auto-reloading and request timing
"""

import time
import os
from os.path import join
import signal
import threading

debug = True
loglevel = 'debug'
#workers = 2
#keepalive = 4

TIMES = {}
def pre_request(worker, req):
    """Gunicorn pre_request hook
    """

    TIMES[worker.pid] = time.time()

def post_request(worker, req, environ = None):
    """Gunicorn post_request hook
    """

    host = dict(req.headers)['HOST']
    cost = time.time() - TIMES[worker.pid]
    url = 'http://%s%s' % (host, req.path)
    print '[%fs] - %s %s' % (cost, req.method, url)


class Reloader(threading.Thread):
    """Auto reloader for auto-reloading gunicorn workers when .py file modified
    """

    def __init__(self, server):
        self.server = server
        threading.Thread.__init__(self)
        self.setDaemon(True)

    def run(self):
        modify_times = {}
        monitor_dirs = os.environ.get('SHEEP_RELOAD_MONITOR_DIRS', '').split(':')

        for monitor_dir in monitor_dirs:
            for root, dirs, files in os.walk(monitor_dir):
                if '/.svn' in root:
                    continue
                for _file in (join(root, name) for name in files):
                    if _file.endswith('.py') or _file.endswith('.ptl') \
                            or _file.endswith('.yaml'):
                        modify_times[_file] = os.stat(_file).st_mtime

        while True:
            #start = time.time()
            for _file, mtime in modify_times.iteritems():
                if mtime != os.stat(_file).st_mtime:
                    print '%s modified, reload workers...' % _file
                    os.kill(self.server.pid, signal.SIGHUP)
                    modify_times[_file] = os.stat(_file).st_mtime
            #print 'Done check, %s seconds spent' % (time.time()-start,)
            time.sleep(2)

def when_ready(server):
    """Gunicorn server ready hook
    """
    Reloader(server).start()
