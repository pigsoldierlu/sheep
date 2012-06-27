#!/usr/bin/python
# encoding: UTF-8

import json
import urllib2
import logging

import pymysql as MySQLdb

from sheep.util import find_app_root, load_dev_config, load_app_config

DEFAULT_SERVER = 'http://deploy.xiaom.co'

logger = logging.getLogger(__name__)

def populate_argument_parser(parser):
    parser.add_argument('root_path', metavar='<app root>', nargs='?',
                      help="directory contains app.yaml "
                           "[default: find automatically in parent dirs]")
    parser.add_argument('-s', '--server', default=DEFAULT_SERVER,
                        help="The AppEngine deploy server [default: %s]" % DEFAULT_SERVER)
    parser.add_argument('-d', '--data', action='store_true', default=False,
                        help="Sync data to remote server"
                             "[default: False]")
    parser.add_argument('--reset', action='store_true', default=False,
                        help="Reset remote server database beforce syncing"
                             "[default: False]")
    parser.add_argument('--dump-mysql', type=str, default='db_dumps.sql',
                        help="Path and filename to store mysql dumping file"
                             "[default: named db_dumps.sql store in current dir]")
    parser.add_argument('--remote', action='store_true',
                        help="Really sync to production database")

def main(args):
    root_path = args.root_path or find_app_root()
    sync_database(root_path, args.dump_mysql, server=args.server, \
                  sync_data=args.data, reset=args.reset, \
                  remote=args.remote)

def sync_database(root_path, dump_mysql, server=DEFAULT_SERVER,
                  sync_data=False, reset=False, remote=False):
    appcfg = load_app_config(root_path)
    devcfg = load_dev_config(root_path)
    if 'mysql' not in devcfg:
        logger.info("No MySQL configuration found in dev.yaml.")
        return 'succeeded'

    logger.info("Dumping database to %s...", dump_mysql)
    with open(dump_mysql, 'w') as dumpfile:
        devcfg['mysql'].setdefault('use_unicode', False)
        devcfg['mysql'].setdefault('charset', 'utf8')
        conn = MySQLdb.connect(**devcfg['mysql'])
        try:
            struct, data = dumps(dumpfile, conn, sync_data)
            appname = appcfg['application']
        finally:
            conn.close()

    if remote:
        logger.info("Syncing database to servers...")
        try:
            result = verify(appname, struct, data, reset, server)
        except:
            logger.exception('Error occured')
            return 'failed'
        return result

def verify(appname, dumps, data, reset, server):
    logger.debug(dumps)
    post_data = json.dumps({'application':appname, 'reset':reset, 'local':dumps, 'data':data})
    post_url = '%s/syncdb/' % server

    req = urllib2.Request(post_url, post_data)
    f = urllib2.urlopen(req)
    line = ''
    for line in iter(f.readline, ''):
        try:
            loglevel, line = line.split(':', 1)
            loglevel = int(loglevel)
        except ValueError:
            loglevel = logging.DEBUG
        logger.log(loglevel, "%s", line.rstrip())
    return line

def dumps(dumpfile, conn, sync_data = False):
    cur = conn.cursor()
    cur.execute(r'SHOW TABLES;')
    tables = cur.fetchall()
    result = []
    data = {}
    for table in tables:
        cur.execute(r'SHOW CREATE TABLE %s;' % table[0])
        struct = []
        result.append({table[0]:[]})
        ret = cur.fetchall()[0][1]
        dumpfile.write(ret + ';')
        dumpfile.write('\r\n')
        for col in ret.split('\n')[1:-1]:
            col = col.strip()
            if not col[0] == '`':
                result[-1][table[0]].append(col.strip(','))
                continue
            struct.append(split_sql(col))
        result[-1][table[0]].append(struct)
        if not sync_data:
            continue
        data[table[0]] = dump_data(conn, dumpfile, table[0])
    cur.close()
    return result, data

def dump_data(conn, dumpfile, table):
    cur = conn.cursor()
    cur.execute(r'SET NAMES UTF8;')
    cur.execute(r'SELECT * FROM %s;' % table)
    rows = cur.fetchall()
    if not rows:
        return []
    datas = []
    for row in rows:
        data = []
        for column in row:
            if isinstance(column, unicode):
                data.append(column.encode('utf-8'))
                continue
            data.append(str(column))
        datas.append(data)
    for data in datas:
        dumpfile.write(json.dumps(data))
        dumpfile.write('\r\n')
    return datas

def split_sql(col):
    col_name = col[1:col.find('`', 1)]
    col_struct = col[col.find('`', 1) + 1:col.rfind(',')].strip()
    return {col_name: col_struct}
