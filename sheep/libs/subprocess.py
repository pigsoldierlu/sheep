"""Implementation of the standard :mod:`subprocess` module that spawns greenlets"""

import os
import sys
import errno
import fcntl

_subprocess = __import__('subprocess')

from gevent import socket, select, hub

# identical to original
CalledProcessError = _subprocess.CalledProcessError
MAXFD = _subprocess.MAXFD
PIPE = _subprocess.PIPE
STDOUT = _subprocess.STDOUT
POPEN = _subprocess.Popen
call = _subprocess.call
check_call = _subprocess.check_call
list2cmdline = _subprocess.list2cmdline

NOT_REPLACE_METHOD = ['write', 'writelines', 'next']

class WrapperPIPE(object):
    def __init__(self, stream):
        self.stream = stream
        self.read = self._sync_read(self.stream.read)
        self.readline = self._sync_read(self.stream.readline)
        self.readlines = self._sync_read(self.stream.readlines)

    def __getattr__(self, name):
        return getattr(self.stream, name)

    def __iter__(self):
        return self

    def next(self):
        while True:
            try:
                return self.stream.next()
            except IOError, ex:
                if ex[0] != errno.EAGAIN:
                    raise StopIteration
                sys.exc_clear()
            socket.wait_read(self.fileno())

    def write(self, data):
        if data:
            bytes_total = len(data)
            bytes_written = 0
            while bytes_written < bytes_total:
                try:
                    bytes_written += os.write(self.fileno(), data[bytes_written:])
                except IOError, ex:
                    if ex[0] != errno.EAGAIN:
                        raise
                    sys.exc_clear()
                socket.wait_write(self.fileno())
            self.flush()

    def writelines(self, data_seq):
        for data in data_seq:
            self.write(data)
        self.flush()

    def _sync_read(self, f):
        def _(size=-1):
            while True:
                try:
                    data = f(size)
                    if not data:
                        break
                    return data
                except IOError, ex:
                    if ex[0] != errno.EAGAIN:
                        raise
                    sys.exc_clear()
                socket.wait_read(self.fileno())
        return _

class Popen(object):
    def __init__(self, *args, **kwargs):
        # delegate to an actual Popen object
        self.__p = POPEN(*args, **kwargs)
        # make the file handles nonblocking
        for pipe in ['stdin', 'stdout', 'stderr']:
            if not getattr(self, pipe, None):
                continue
            p = getattr(self, pipe)
            fcntl.fcntl(p, fcntl.F_SETFL, os.O_NONBLOCK)
            setattr(self, pipe, WrapperPIPE(p))

    def __getattr__(self, name):
        # delegate attribute lookup to the real Popen object
        return getattr(self.__p, name)

    def communicate(self, input=None):
        # Optimization: If we are only using one pipe, or no pipe at
        # all, using select() is unnecessary.
        if [self.stdin, self.stdout, self.stderr].count(None) >= 2:
            stdout = None
            stderr = None
            if self.stdin:
                self.stdin.write(input)
            elif self.stdout:
                stdout = self.stdout.read()
            elif self.stderr:
                stderr = self.stderr.read()
            self.wait()
            return (stdout, stderr)
        else:
            return self._communicate(input)

    def _communicate(self, input):
        # identical to original... all the heavy lifting is done
        # in gevent.select.select
        read_set = []
        write_set = []
        stdout = None # Return
        stderr = None # Return

        if self.stdin:
            # Flush stdin buffer.
            self.stdin.flush()
            if input:
                write_set.append(self.stdin)
            else:
                self.stdin.close()
        if self.stdout:
            read_set.append(self.stdout)
            stdout = []
        if self.stderr:
            read_set.append(self.stderr)
            stderr = []

        input_offset = 0
        while read_set or write_set:
            try:
                rlist, wlist, xlist = select.select(read_set, write_set, [])
            except select.error, e:
                if e.args[0] == errno.EINTR:
                    continue
                raise

            if self.stdin in wlist:
                # When select has indicated that the file is writable,
                # we can write up to PIPE_BUF bytes without risk
                # blocking.  POSIX defines PIPE_BUF >= 512
                bytes_written = os.write(self.stdin.fileno(), buffer(input, input_offset, 512))
                input_offset += bytes_written
                if input_offset >= len(input):
                    self.stdin.close()
                    write_set.remove(self.stdin)

            if self.stdout in rlist:
                data = os.read(self.stdout.fileno(), 1024)
                if data == "":
                    self.stdout.close()
                    read_set.remove(self.stdout)
                stdout.append(data)

            if self.stderr in rlist:
                data = os.read(self.stderr.fileno(), 1024)
                if data == "":
                    self.stderr.close()
                    read_set.remove(self.stderr)
                stderr.append(data)

        # All data exchanged.  Translate lists into strings.
        if stdout is not None:
            stdout = ''.join(stdout)
        if stderr is not None:
            stderr = ''.join(stderr)

        # Translate newlines, if requested.  We cannot let the file
        # object do the translation: It is based on stdio, which is
        # impossible to combine with select (unless forcing no
        # buffering).
        if self.universal_newlines and hasattr(file, 'newlines'):
            if stdout:
                stdout = self._translate_newlines(stdout)
            if stderr:
                stderr = self._translate_newlines(stderr)

        self.wait()
        return (stdout, stderr)

    def wait(self, check_interval=0.01):
        # non-blocking, use hub.sleep
        try:
            while True:
                status = self.poll()
                if status >= 0:
                    return status
                hub.sleep(check_interval)
        except OSError, e:
            if e.errno == errno.ECHILD:
                # no child process, this happens if the child process
                # already died and has been cleaned up
                return -1
            else:
                raise
