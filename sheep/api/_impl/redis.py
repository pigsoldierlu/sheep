#!/usr/local/bin/python2.7
#coding:utf-8

from __future__ import absolute_import
from redis import ConnectionPool, Redis

def client(*args, **kwargs):
    return Redis(*args, **kwargs)
