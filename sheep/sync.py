#!/opt/local/bin/python2.7
#coding:utf-8

import os
import logging
from subprocess import check_call

from .util import find_app_root, load_app_config, get_vcs, is_pip_compatible
from .consts import VENV_DIR_KEY, DEFAULT_VENV_DIR

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
    else:
        logger.error("%s is not under version control", approot)
        return 1

    if not os.path.exists(os.path.join(approot, 'permdir')):
        os.mkdir(os.path.join(approot, 'permdir'))

    if not os.path.exists(venvdir):
        logger.info('Creating virtualenv at %s...', venvdir)
        check_call(['virtualenv', '--no-site-packages', venvdir,
                    '--prompt', '(%s)' % appname])

    #if not os.path.exists(os.path.join(venvdir, 'src', 'pip')) \
    #   or not is_pip_compatible(os.path.join(venvdir, 'bin', 'pip')):
    #    logger.info('Installing patched pip...')
    #    check_call([os.path.join(venvdir, 'bin', 'pip'), 'install', '-e',
    #                'hg+http://shire:hobbits@hg.douban.com/pip#egg=pip'])

    if os.path.exists(os.path.join(approot, 'pip-req.txt')):
        logger.info('Installing requirements...')
        check_call([os.path.join(venvdir, 'bin', 'pip'), 'install',
                    '-r', os.path.join(approot, 'pip-req.txt'),
                    '--index-url', 'file://%s/pip-download/' % approot,
                    '--extra-index-url', 'http://pypi.python.org/simple/',
                    '--find-links', 'file://%s/pip-download/' % approot,
                   ])

    if os.path.exists(os.path.join(approot, 'setup.py')):
        logger.info("Running python setup.py develop")
        check_call([os.path.join(venvdir, 'bin', 'python'), 'setup.py',
                    'develop'])

    logger.info('Sync success...')
