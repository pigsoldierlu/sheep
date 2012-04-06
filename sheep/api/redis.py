#!/usr/bin/python
# encoding: UTF-8

from __future__ import absolute_import
from redis import ConnectionPool, Redis

def client(*args, **kwargs):
    return Redis(*args, **kwargs)
