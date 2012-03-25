#!/usr/local/bin/python2.7
#coding:utf-8

import logging
import functools
from werkzeug.contrib import cache

logger = logging.getLogger(__name__)

class Cache(object):
    def __init__(self, prefix, timeout=0):
        self._cache = cache.FileSystemCache('/tmp')
        self._prefix = prefix
        self._timeout = timeout

    def __call__(self, f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            if args:
                key = self._prefix + ':' + '-'.join(str(a) for a in args)
            else:
                key = self._prefix

            if kwargs:
                for k, v in kwargs.iteritems():
                    key += '%s#%s' % (k, v)

            value = self._cache.get(key)
            if not value:
                value = f(*args, **kwargs)
                try:
                    logger.info('set cache %s' % key)
                    self._cache.set(key, value, self._timeout)
                except Exception, e:
                    logger.warn('cache error: %s, exception: %s' % (key, e))
                    pass
            else:
                logger.info('get cache %s' % key)
            return value
        return wrapper

