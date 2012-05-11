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
        monitor_dirs = os.environ.get('SHEEP_RELOAD_MONITOR_DIRS', '').split(':')
        modify_times = gen_files(monitor_dirs)

        while os.getpid() == self.server.pid:   # do not monitor in worker processes
            #start = time.time()
            for _file, mtime in modify_times.items():
                try:
                    if mtime != os.stat(_file).st_mtime:
                        print '%s modified, reload workers...' % _file
                        os.kill(self.server.pid, signal.SIGHUP)
                        modify_times[_file] = os.stat(_file).st_mtime
                except OSError, e:
                    print "%s deleted, reload workers..." % _file
                    os.kill(self.server.pid, signal.SIGHUP)
                    del modify_times[_file]

            new_modify_times = gen_files(monitor_dirs)
            add_files = set(new_modify_times).difference(modify_times)
            if add_files:
                print 'add files', add_files
                os.kill(self.server.pid, signal.SIGHUP)
                modify_times = new_modify_times

            #print 'Done check, %s seconds spent' % (time.time()-start,)
            time.sleep(2)

def gen_files(monitor_dirs):
    modify_times = {}
    for monitor_dir in monitor_dirs:
        for root, dirs, files in os.walk(monitor_dir):
            if '/.svn' in root:
                continue
            for _file in (join(root, name) for name in files):
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
