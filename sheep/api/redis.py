#!/usr/bin/python
# encoding: UTF-8

from redis import ConnectionPool, Redis

def client(*args, **kwargs):
    return Redis(*args, **kwargs)
