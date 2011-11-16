#!/usr/bin/python
# encoding: UTF-8

import sys, os
from subprocess import Popen, PIPE, CalledProcessError
from collections import defaultdict
from urllib import FancyURLopener, urlencode
import logging

from .syncdb import sync_database
from .util import load_app_config, find_app_root, activate_virtualenv, \
        log_check_call, log_call, dump_requirements, get_vcs_url, get_vcs

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
    parser.add_argument('-s', '--server', default='http://dae_deploy.dapps.douban.com',
                        help="The AppEngine deploy server "
                             "[default: http://dae_deploy.dapps.douban.com]")
    parser.add_argument('root_path', metavar='<app root>', nargs='?',
                      help="directory contains app.yaml "
                           "[default: find automatically in parent dirs]")
    parser.add_argument('--dump-mysql', type=str, default='db_dumps.sql',
                        help="Path and filename to store mysql dumping file"
                             "[default: named db_dumps.sql store in current dir]")
    parser.add_argument('--deploy-server', default=None,
                        help="Choose dae_deploy server [default: random] "
                            "(debug purpose only)")

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
    sync_database(root_path, args.dump_mysql, args.server)

    logger.info("Generating dependencies...")
    dump_requirements(root_path)

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
    if logger.getEffectiveLevel() < logging.INFO:
        data['verbose'] = '1'

    opener = FancyURLopener()
    if args.deploy_server:
        opener.addheader('Cookie',
                         '_dae_app_server=%s' % args.deploy_server)
    f = opener.open(args.server, urlencode(data))
    line = ''  # to avoid NameError for line if f has no output at all.
    for line in iter(f.readline, ''):
        try:
            loglevel, line = line.split(':', 1)
            loglevel = int(loglevel)
        except ValueError:
            loglevel = logging.DEBUG
        logger.log(loglevel, "%s", line.rstrip())

    if not any(word in line for word in ['succeeded', 'failed']):
        logger.warning("It seems that the deploy failed.  Try again later.  "
                       "If the failure persists, contact DAE admin please.")

def check_dependency_modifications():
    virtualenv = sys.prefix
    src_path = os.path.join(virtualenv, 'src')
    for dirname in os.listdir(src_path):
        dirpath = os.path.join(src_path, dirname)
        if not os.path.isdir(dirpath):
            continue
        logger.info("Checking %s", dirpath)
        vcs = get_vcs(dirpath)
        if vcs == 'hg':
            check_hg_modifications(dirpath)
        elif vcs == 'svn':
            check_svn_modifications(dirpath)
        elif vcs == 'git':
            check_git_modifications(dirpath)


def check_hg_modifications(dirpath):
    modified = Popen(['hg', '-R', dirpath, 'status', '-mard'],
                     stdout=PIPE).communicate()[0].strip()
    if modified:
        raise LocalModificationExists(dirpath)
    cmd = ['hg', '-R', dirpath, 'outgoing']
    retcode, output = call(cmd, record_output=True)
    if retcode == 0:
        raise OutgoingChangesExists(dirpath)
    elif retcode != 1:
        raise CalledProcessError(retcode, cmd, output=output)

def check_git_modifications(dirpath):
    cwd = os.getcwd()
    try:
        os.chdir(dirpath)
        modified = Popen(['git', 'status', '--short'],
                         stdout=PIPE).communicate()[0].strip()
        if modified:
            raise LocalModificationExists(dirpath)
        has_outgoing = Popen(['git', 'log', 'origin/master..HEAD'],
                             stdout=PIPE).communicate()[0].strip()
        if has_outgoing:
            raise OutgoingChangesExists(dirpath)

    finally:
        os.chdir(cwd)

def check_svn_modifications(dirpath):
    modified = Popen(['svn', 'status', dirpath],
                     stdout=PIPE).communicate()[0].strip()
    if modified:
        raise LocalModificationExists(dirpath)

def push_modifications(root_path):
    if os.path.exists(os.path.join(root_path, '.hg')):
        push_hg_modifications(root_path)
    elif os.path.exists(os.path.join(root_path, '.svn')):
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
                    '-m', "update pip-req.txt by dae deploy"])

    check_call(['hg', '-R', root_path, 'push'])

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
            check_call(['svn', 'commit', root_path], need_input=True)

    elif svn_status.values() == [[pip_req_path]]:
        check_call(['svn', 'commit', root_path,
                    '-m', "update pip-req.txt by dae deploy"])


