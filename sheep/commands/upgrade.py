#!/usr/local/bin/python2.7
#coding:utf-8

import re
import os
import logging
from subprocess import Popen, PIPE, STDOUT

sdk_svn = 'http://ursa.googlecode.com/svn/sheep-farm/sheep'
sdk_path = os.path.dirname(os.path.realpath(__file__))

def populate_argument_parser(parser):
    parser.add_argument('--up', action='store_true', default=False,
                        help="upgrade sdk [default: false]")

def main(args):
    flag, rv, lv = check_version()
    if flag:
        ret = 'SDK need upgrade\n'
        ret += 'Remote revision: %d\n' % rv
        ret += 'Local revision: %d\n' % lv
        ret += 'Plz use sheep upgrade --up'
    else:
        ret = 'SDK up-to-date'
    if not flag or not args.up:
        return ret

    package_path = os.path.dirname(os.path.dirname(sdk_path))
    target_path = os.path.dirname(package_path)
    upgrade_sdk(target_path, package_path)

def upgrade_sdk(target_path, package_path):
    install = os.path.join(package_path, 'install.py')
    paths = os.environ['PATH'].split(':')
    execute_path = paths[0]
    virtual_path = os.environ.get('VIRTUAL_ENV', None)
    new_paths = []
    for i in paths:
        if execute_path in i:
            continue
        if virtual_path and virtual_path in i:
            continue
        new_paths.append(i)
    os.environ['PATH'] = ':'.join(new_paths)
    os.execvpe('python', ['python', install, target_path], env=os.environ)

def check_version():
    p = Popen(['svn', 'info', sdk_path, '--xml'], stdout=PIPE, stderr=STDOUT)
    out = p.communicate()[0]
    m = re.compile(r'(commit\n\s+revision=\"(?P<revision>\d+)\")', re.MULTILINE).search(out)
    if not m:
        print 'get svn info failed: %s not a svn directory or password not saved?' % sdk_path
        return False, '', ''
    local_revision = int(m.groupdict()['revision'])
    p = Popen(['svn', 'log', sdk_svn, '-q'], stdout=PIPE, stderr=STDOUT)
    for i in xrange(0, 2):
        line = p.stdout.readline().strip()
    try:
        remote_revision = int(line.split(' ', 1)[0][1:])
    except ValueError:
        logging.info('get svn log failed: %s' % line)
        return False, '', ''
    return remote_revision > local_revision, remote_revision, local_revision

if __name__ == '__main__':
    check_version()

