#!/usr/local/bin/python2.7
#coding:utf-8

import os
import web
import socket
import gevent_profiler
from sheep.app import SHEEPApplication

urls = (
    '/_dev/profile/', 'profile',
)

app = web.application(urls, globals()).wsgifunc()

FORM_HTML = r'''
<form action="/_dev/profile/" method="get">
    <label for="req_count">需要分析的request数目:</label>
    <input type="text" name="_sheep_profile_count" value="100" />
    <input type="hidden" name="_sheep_app_server" value="%s" />
    <input type="submit" value="开始分析" />
</form>'''

FRESH_HTML = r'''
%d/%d<a href="/_dev/profile/?_sheep_profile_count=%d&_sheep_app_server=%s&_sheep_pid=%d">刷新</a>
'''

def output(stat_file):
    yield '<pre>'
    for line in open(stat_file, 'r').xreadlines():
        yield line
    yield '</pre>'

class profile:
    def GET(self):
        web.header('Content-Type', 'text/html')
        oid = status()
        if not oid and web.ctx.env['SERVER_NAME'] != '127.0.0.1' and \
                web.ctx.env['SERVER_NAME'] != 'localhost':
            return 'please log in: ' + webopenid.form('/_dev/profile/openid')
        params = web.input(_sheep_app_server=None, _sheep_profile_count=None, _sheep_pid=None)
        if not web.ctx.env.get('QUERY_STRING', None):
            return FORM_HTML % socket.gethostname()

        count = params._sheep_profile_count
        backend = params._sheep_app_server
        pid = params._sheep_pid
        if not (count and backend):
            return '''params invaild'''
        count = int(count)
        if not pid:
            pid = os.getpid()
            raise web.seeother("/_dev/profile/?_sheep_profile_count=%d&_sheep_app_server=%s&_sheep_pid=%d" % \
                    (count, backend, pid))
        else:
            pid = int(pid)

        html = FRESH_HTML
        num_file = os.path.join('/tmp','%s.%d.counter' % (web.ctx.env['SERVER_NAME'], pid))
        stat_file = os.path.join('/tmp', '%s.%d.prof' % (web.ctx.env['SERVER_NAME'], pid))
        now = os.path.getsize(num_file) if os.path.exists(num_file) else 0
        html = html % (now, count, count, backend.encode('utf8'), pid)

        if not getattr(SHEEPApplication, 'old_call', None):
            setattr(SHEEPApplication, 'old_call', SHEEPApplication.__call__)

        if not os.path.exists(num_file) and os.path.exists(stat_file):
            return output(stat_file)
        elif not os.path.exists(num_file):
            with open(num_file, 'w+') as f:
                f.write('')

            gevent_profiler.set_stats_output(stat_file)
            gevent_profiler.set_trace_output(None)

            def monkey_call(obj, environ, start_response):
                if os.path.exists(num_file):
                    with open(num_file, 'a') as f:
                        f.write('1')
                return obj.old_call(environ, start_response)
            SHEEPApplication.__call__ = monkey_call
            gevent_profiler.attach()
        elif os.path.getsize(num_file) >= count:
            os.remove(num_file)
            try:
                gevent_profiler.detach()
            except:
                pass
            SHEEPApplication.__call__ = SHEEPApplication.old_call
            return output(stat_file)
        return html

if __name__ == "__main__":
    app.run()
