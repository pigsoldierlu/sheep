#!/usr/bin/python
# encoding: UTF-8

from pool.pool import QueuePool
from MySQLdb import connect as _connect

MAX_OVERFLOW = 20
POOL_SIZE = 5
TIMEOUT = 10

pool = QueuePool(_connect, max_overflow=MAX_OVERFLOW, pool_size=POOL_SIZE, timeout=TIMEOUT)
def connect():
    return pool.connect()

