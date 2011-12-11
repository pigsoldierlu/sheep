#!/usr/bin/python
# encoding: UTF-8

import os, sys, json
from subprocess import Popen, PIPE, CalledProcessError
from collections import defaultdict
from urllib import FancyURLopener, urlencode
import logging

from .syncdb import sync_database
from .util import load_app_config, find_app_root, activate_virtualenv, \
        log_check_call, log_call, dump_requirements, get_vcs_url, get_vcs

logger = logging.getLogger(__name__)
result = {}

RED = '\x1b[01;31m'
GREEN = '\x1b[01;32m'
NORMAL = '\x1b[0m'

def render_ok(msg):
    return GREEN + msg + NORMAL

def render_err(msg):
    return RED + msg + NORMAL

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
    parser.add_argument('--suffix', default='.xiaom.co',
                        help="The AppEngine deploy server suffix "
                             "[default: *.xiaom.co]")
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
    appname = appcfg['application']
    activate_virtualenv(root_path)

    servers = get_deploy_servers(args.server, appname)
    if not servers:
        logger.info("No deploy servers allow")
        sys.exit(1)
    servers = ['http://%s%s' % (prefix, args.suffix) for prefix in servers]
    logger.info(render_ok("Application allowed to deploy those servers"))
    for server in servers:
        logger.info(render_ok(server))

    ret = sync_database(root_path, args.dump_mysql, servers[0])
    if 'succeeded' not in ret:
        logger.info("Syncdb failed, deploy exit ...")
        sys.exit(1)

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
    data = {'app_name': appname,
            'app_url': vcs_url}
    if logger.getEffectiveLevel() < logging.INFO:
        data['verbose'] = '1'
    deploy_to_server(data, servers[0])
    if result[servers[0]] == 'Failed':
        logger.warning(render_err("It seems that the deploy failed.  Try again later. If the failure persists, contact DAE admin please."))
        sys.exit(1)

    servers.pop(0)
    for server in servers:
        sync_database(root_path, args.dump_mysql, server)
        deploy_to_server(data, server)
    logger.info('==========RESULT==========')
    for k, v in result.iteritems():
        if v == 'Failed':
            logger.info(render_err("%s %s" % (k, v)))
        else:
            logger.info(render_ok("%s %s" % (k, v)))

def get_deploy_servers(server, appname):
    opener = FancyURLopener()
    f = opener.open(os.path.join(server, 'dispatch', appname))
    try:
        return json.loads(f.read())
    except:
        return []

def deploy_to_server(data, server):
    global result
    opener = FancyURLopener()
    f = opener.open(server, urlencode(data))
    line = ''  # to avoid NameError for line if f has no output at all.
    for line in iter(f.readline, ''):
        try:
            loglevel, line = line.split(':', 1)
            loglevel = int(loglevel)
        except ValueError:
            loglevel = logging.DEBUG
        logger.log(loglevel, "%s", line.rstrip())

    if not any(word in line for word in ['succeeded', 'failed']):
        result[server] = 'Failed'
    else:
        result[server] = 'Succeeded'

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


