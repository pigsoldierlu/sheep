#!/usr/bin/python
# encoding: UTF-8

from pool.pool import QueuePool
from MySQLdb import connect as _connect

MAX_OVERFLOW = 20
POOL_SIZE = 5
TIMEOUT = 10

pools = {}
def connect(*a, **kw):
    key = (a, tuple(sorted(kw.items())))
    pool = pools.get(key)
    if pool is None:
        def conn():
            return _connect(*a, **kw)
        pool = QueuePool(conn, max_overflow=MAX_OVERFLOW, pool_size=POOL_SIZE, timeout=TIMEOUT)
        pools[key] = pool
    return pool.connect()

def get_mysql_conn_params():
    pass
