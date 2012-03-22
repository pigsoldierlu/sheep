#!/usr/bin/python
# encoding: UTF-8

import os
import logging
import unittest

from sheep.api import mysql

logger = logging.getLogger(__name__)

def create_test_yaml():
    #TODO
    raise NotImplementedError

class TestCase(unittest.TestCase):
    def setUp(self):
        assert os.environ['SHEEP_DEV_YAML'] == 'test.yaml'

        approot = os.environ['SHEEP_APPROOT']
        schema_path = os.path.join(approot, 'db_dumps.sql')
        if os.path.exists(schema_path):
            conn = mysql.connect()
            curs = conn.cursor()
            curs.execute("show tables")
            for table in curs:
                curs.execute("drop table %s" % table)
            sqls = open(schema_path).read().split(';')
            for sql in sqls:
                curs.execute(sql)
            conn.commit()

    def tearDown(self):
        pass
