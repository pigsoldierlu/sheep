#!/usr/bin/python
# encoding: UTF-8

import os
import time
import signal
import threading

debug = True
loglevel = 'debug'
accesslog = '-'
access_log_format = """%(t)s "%(r)s" %(s)s %(b)s %(HTTP_X_SHEEP_REQUEST_TIME_IN_MS)sms"""

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
                for _file in (os.path.join(root, name) for name in files):
                    if _file.endswith('.py') or _file.endswith('.ptl') \
                            or _file.endswith('.yaml'):
                        modify_times[_file] = os.stat(_file).st_mtime

        while os.getpid() == self.server.pid:
            #start = time.time()
            for _file, mtime in modify_times.iteritems():
                if not os.path.exists(_file):
                    # file deleted
                    print "%s deleted, reload workers..." % _file
                    os.kill(self.server.pid, signal.SIGHUP)
                    del modify_times[_file]

                elif mtime != os.stat(_file).st_mtime:
                    print '%s modified, reload workers...' % _file
                    os.kill(self.server.pid, signal.SIGHUP)
                    modify_times[_file] = os.stat(_file).st_mtime
            #print 'Done check, %s seconds spent' % (time.time()-start,)
            time.sleep(2)

def when_ready(server):
    """Gunicorn server ready hook
    """

    Reloader(server).start()
