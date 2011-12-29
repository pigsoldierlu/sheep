#!/usr/bin/python
# encoding: UTF-8

import os, sys, json
from subprocess import Popen, PIPE, STDOUT, CalledProcessError
from collections import defaultdict
from urllib import FancyURLopener, urlencode
import logging

from .syncdb import sync_database
from .statics import mirror_statics
from .util import load_app_config, find_app_root, activate_virtualenv, \
        log_check_call, log_call, get_vcs_url

logger = logging.getLogger(__name__)

def check_call(*args, **kwargs):
    kwargs.setdefault('log', logger.debug)
    return log_check_call(*args, **kwargs)

def call(*args, **kwargs):
    kwargs.setdefault('log', logger.debug)
    return log_call(*args, **kwargs)

class LocalModificationExists(Exception):
    def __init__(self, workdir):
        self.workdir = workdir

class OutgoingChangesExists(Exception):
    def __init__(self, workdir):
        self.workdir = workdir

def populate_argument_parser(parser):
    parser.add_argument('-s', '--server', default='http://deploy.xiaom.co',
                        help="The AppEngine deploy main server "
                             "[default: http://deploy.xiaom.co]")
    parser.add_argument('--fast', default=False,
                        help="Deploy on all nodes in parallel. "
                             "Availability may be affected.")
    parser.add_argument('root_path', metavar='<app root>', nargs='?',
                      help="directory contains app.yaml "
                           "[default: find automatically in parent dirs]")
    parser.add_argument('--dump-mysql', type=str, default='db_dumps.sql',
                        help="Path and filename to store mysql dumping file"
                             "[default: named db_dumps.sql store in current dir]")

def main(args):
    try:
        return _main(args)
    except CalledProcessError, e:
        logger.exception("Error when call subprocess:")
        if e.output:
            logger.error("Output of the subprocess follows:\n" +
                         e.output.rstrip())
        return 1

def _main(args):
    root_path = args.root_path or find_app_root()
    appcfg = load_app_config(root_path)
    activate_virtualenv(root_path)

    ret = sync_database(root_path, args.dump_mysql, args.server)
    if 'succeeded' not in ret:
        logger.info("Syncdb failed, deploy exit ...")
        sys.exit(1)

    logger.info("Pushing modifications...")
    push_modifications(root_path)

    vcs_url = get_vcs_url(root_path)
    if not vcs_url:
        logger.error("%s is not under version control. abort.", root_path)
        sys.exit(1)
    logger.debug("app url: %s", vcs_url)

    logger.info("Deploying to servers...")
    data = {'app_name': appcfg['application'],
            'app_url': vcs_url}

    if args.fast:
        data['fast'] = '1'

    ret = deploy_to_server(data, args.server)
    if ret == 'Failed':
        logger.warning("It seems that the deploy failed.  Try again later.  "
                       "If the failure persists, contact DAE admin please.")
        sys.exit(1)

    ret = mirror_statics(root_path, args.server)
    if 'succeeded' not in ret:
        logger.info("Mirror failed, deploy exit ...")
        sys.exit(1)

def deploy_to_server(data, server):
    opener = FancyURLopener()
    verbose = logger.getEffectiveLevel()
    f = opener.open(server, urlencode(data))
    line = ''  # to avoid NameError for line if f has no output at all.
    for line in iter(f.readline, ''):
        try:
            loglevel, line = line.split(':', 1)
            loglevel = int(loglevel)
        except ValueError:
            loglevel = logging.DEBUG
        if loglevel >= verbose:
            logger.log(loglevel, "%s", line.rstrip())

    if not any(word in line for word in ['succeeded', 'failed']):
        return 'Failed'
    else:
        return 'Succeeded'

def scm_type(root_path):
    '''Get type of SCM(Software Configuration Management)'''

    if os.path.exists(os.path.join(root_path, '.hg')):
        return 'hg'
    elif os.path.exists(os.path.join(root_path, '.svn')):
        return 'svn'

def push_modifications(root_path):
    scm = scm_type(root_path)
    if scm == 'hg':
        push_hg_modifications(root_path)
    elif scm == 'svn':
        push_svn_modifications(root_path)

def push_hg_modifications(root_path):
    call(['hg', '-R', root_path, 'pull', '--update'])
    call(['hg', '-R', root_path, 'add', 'pip-req.txt'])
    p = Popen(['hg', '-R', root_path, 'status', '-mard'], stdout=PIPE)
    hg_status = defaultdict(list)
    for line in p.stdout:
        status, filename = line.split()
        hg_status[status].append(filename)

    if hg_status and hg_status.values() != [['pip-req.txt']]:
        logger.warning("You have local modification, listed as followed:")
        check_call(['hg', '-R', root_path, 'status'], log=logger.warning)
        answer = raw_input("Commit them? (y/n) ")
        if answer != 'y':
            sys.exit(1)
        else:
            check_call(['hg', '-R', root_path, 'commit'], need_input=True)

    elif hg_status.values() == [['pip-req.txt']]:
        check_call(['hg', '-R', root_path, 'commit',
                    '-m', "update pip-req.txt by deploy"])

    check_call(['hg', '-R', root_path, 'push'], need_input=True)

def push_svn_modifications(root_path):
    call(['svn', 'update', root_path], log=logger.debug)
    call(['svn', 'add', os.path.join(root_path, 'pip-req.txt')])
    p = Popen(['svn', 'status', root_path, '-q'], stdout=PIPE)
    svn_status = defaultdict(list)
    for line in p.stdout:
        status, filename = line.split()
        svn_status[status].append(filename)

    pip_req_path = os.path.join(root_path, 'pip-req.txt')

    if svn_status and svn_status.values() != [[pip_req_path]]:
        logger.warning("You have local modification, listed as followed:")
        check_call(['svn', 'status', root_path], log=logger.warning)
        answer = raw_input("Commit them? (y/n) ")
        if answer != 'y':
            sys.exit(1)
        else:
            try:
                check_call(['svn', 'commit', root_path], need_input=True)
            except:
                logger.info('You need set svn commit editor first.')
                sys.exit(1)

    elif svn_status.values() == [[pip_req_path]]:
        check_call(['svn', 'commit', root_path,
                    '-m', "update pip-req.txt by deploy"])


