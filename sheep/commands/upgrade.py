#!/usr/local/bin/python2.7
#coding:utf-8

import logging
import os
from subprocess import Popen, PIPE, call, check_call

from dae.util import chdir

REPO_URL = 'git://github.com/xiaomen/sheep.git'
RELEASE_BRANCH = 'master'

sdk_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
logger = logging.getLogger(__name__)

def populate_argument_parser(parser):
    parser.add_argument('--up', action='store_true', default=False,
                        help="upgrade sdk [default: false]")

def main(args):
    if args.up:
        return upgrade_sdk(sdk_path)

    else:
        flag, rv, lv = check_version()
        if flag:
            logger.warning("A new version of SHEEP SDK has been released!")
            logger.warning("Run `sheep upgrade --up` to upgrade SDK")
        else:
            logger.info('Your SDK is up to date')


def upgrade_sdk(path):
    venv_bin = os.path.join(path, 'venv', 'bin')
    os.environ['PATH'] = ':'.join(x for x in os.environ['PATH'].split(':')
                                  if x != venv_bin)
    with chdir(path):
        check_call(['git', 'pull', REPO_URL, RELEASE_BRANCH])
        return call(['python', 'install.py'])

def check_version():
    logger.debug("Getting local revision")
    local_rev = get_local_revision(sdk_path)
    logger.debug("Local revision: %s", local_rev)
    logger.debug("Getting remote revision")
    remote_rev = get_remote_revision(sdk_path)
    logger.debug("Remote revision: %s", remote_rev)
    return local_rev != remote_rev, remote_rev, local_rev


def get_local_revision(path):
    with chdir(path):
        return Popen(['git', 'rev-parse', 'HEAD'],
                     stdout=PIPE).communicate()[0].strip()

def get_remote_revision(path):
    with chdir(path):
        check_call(['git', 'fetch', REPO_URL, RELEASE_BRANCH],
                   stderr=open('/dev/null', 'w'))
        return Popen(['git', 'rev-parse', 'FETCH_HEAD'],
                     stdout=PIPE).communicate()[0].strip()




if __name__ == '__main__':
    check_version()

