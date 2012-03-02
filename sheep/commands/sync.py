#!/usr/bin/python
# encoding: UTF-8

import os
import logging
from subprocess import check_call

from sheep.consts import VENV_DIR_KEY, DEFAULT_VENV_DIR
from sheep.util import find_app_root, load_app_config, get_vcs, is_pip_compatible

logger = logging.getLogger(__name__)

def populate_argument_parser(parser):
    parser.add_argument('root_path', metavar="<app root>", nargs='?',
                        help="directory contains app.yaml "
                        "[default: find automatically in parent dirs]")

def main(args):
    approot = os.path.abspath(args.root_path or find_app_root())
    appcfg = load_app_config(approot)
    appname = appcfg['application']
    venvdir = os.path.join(approot,
                           appcfg.get(VENV_DIR_KEY, DEFAULT_VENV_DIR))

    vcs = get_vcs(approot)
    if vcs == 'hg':
        check_call(['hg', '-R', approot,  'pull', '-u'])
    elif vcs == 'svn':
        check_call(['svn', 'up', approot])
    elif vcs == 'git':
        check_call(['git', 'pull', approot])
    else:
        logger.error("%s is not under version control", approot)
        return 1

    if not os.path.exists(os.path.join(approot, 'permdir')):
        os.mkdir(os.path.join(approot, 'permdir'))

    if not os.path.exists(venvdir):
        logger.info('Creating virtualenv at %s...', venvdir)
        check_call(['virtualenv', '--no-site-packages', venvdir,
                    '--prompt', '(%s)' % appname])

    if not is_pip_compatible(os.path.join(venvdir, 'bin', 'pip')):
        logger.info('Installing patched pip...')
        check_call([os.path.join(venvdir, 'bin', 'pip'), 'install', '-U',
                    'hg+https://bitbucket.org/CMGS/pip'])

    if os.path.exists(os.path.join(approot, 'pip-req.txt')):
        logger.info('Installing requirements...')
        check_call([os.path.join(venvdir, 'bin', 'pip'), 'install',
                    '-r', os.path.join(approot, 'pip-req.txt'),
                    '--save-download', os.path.join(approot, 'pip-download'),
                    '--no-index',
                    '--find-links', 'file://%s/pip-download/' % approot,
                    '--fallback-index-url', 'http://pypi.python.org/simple/',
                   ])

    if os.path.exists(os.path.join(approot, 'setup.py')):
        logger.info("Running python setup.py develop")
        check_call([os.path.join(venvdir, 'bin', 'python'), 'setup.py',
                    'develop'])

    logger.info('Sync success...')
