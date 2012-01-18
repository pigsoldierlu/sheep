#!/usr/local/bin/python2.7
#coding:utf-8

import re
import os
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
    if not args.up:
        return ret

    package_path = os.path.dirname(sdk_path)
    target_path = os.path.dirname(package_path)
    upgrade_sdk(target_path, package_path)

def upgrade_sdk(target_path, package_path):
    install = os.path.join(package_path, 'install.py')
    paths = os.environ['PATH'].split(':')
    paths.reverse()
    os.environ['PATH'] = ':'.join(paths)
    os.execvpe('python', ['python', install, target_path], env=os.environ)

def check_version():
    p = Popen(['svn', 'info', sdk_path, '--xml'], stdout=PIPE, stderr=STDOUT)
    out = p.communicate()[0]
    m = re.compile(r'(commit\n\s+revision=\"(?P<revision>\d+)\")', re.MULTILINE).search(out)
    local_revision = int(m.groupdict()['revision'])
    p = Popen(['svn', 'log', sdk_svn, '-q'], stdout=PIPE, stderr=STDOUT)
    for i in xrange(0, 2):
        line = p.stdout.readline().strip()
    remote_revision = int(line.split(' ', 1)[0][1:])
    return remote_revision > local_revision, remote_revision, local_revision

if __name__ == '__main__':
    check_version()

