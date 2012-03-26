# -*- coding: utf-8 -

import re

def dispatcher(environ, start_response):
    path = environ['PATH_INFO']
    pattern = re.compile('/_sheep/(?P<api>.+?)/.*', re.I)
    match = pattern.match(path)
    if not match:
        start_response('404 Not Found', [])
        return ['Not Found']
    api = match.group('api')
    manager_module = __import__('', globals(), locals(), fromlist=[api],
                                level=1)
    return getattr(manager_module, api).app(environ, start_response)
