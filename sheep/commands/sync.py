#!/usr/bin/python
# encoding: UTF-8

import re
import os
import sys
import logging
from subprocess import check_call, call, Popen, PIPE

from sheep.util import find_app_root, load_app_config, get_vcs, \
        is_pip_compatible, get_venvdir

logger = logging.getLogger(__name__)
here = os.path.dirname(__file__)

def populate_argument_parser(parser):
    parser.add_argument('root_path', metavar="<app root>", nargs='?',
                        help="directory contains app.yaml "
                        "[default: find automatically in parent dirs]")

def main(args):
    approot = os.path.abspath(args.root_path or find_app_root())
    appcfg = load_app_config(approot)
    appname = appcfg['application']
    venvdir = get_venvdir(approot)

    vcs = get_vcs(approot)
    if vcs == 'hg':
        check_call(['hg', '-R', approot,  'pull', '-u'])
    elif vcs == 'svn':
        check_call(['svn', 'up', approot])
    elif vcs == 'git':
        try:
            check_call(['git', '--git-dir', os.path.join(approot, '.git'),
                        '--work-tree', approot, 'pull'])
        except:
            call(['git', '--git-dir', os.path.join(approot, '.git'), 'pull'])
    else:
        logger.error("%s is not under version control", approot)
        return 1

    if not os.path.exists(os.path.join(approot, 'permdir')):
        os.mkdir(os.path.join(approot, 'permdir'))

    if not os.path.exists(venvdir):
        pkgdir = os.path.join(os.path.dirname(os.path.dirname(here)),
                              '3rdparty')
        logger.info('Creating virtualenv at %s...', venvdir)
        check_call(['python', os.path.join(pkgdir, 'virtualenv.py'),
                    '--no-site-packages',
                    '--distribute',
                    '--extra-search-dir', pkgdir,
                    '--never-download',
                    '--prompt', '(%s)' % appname,
                    venvdir])

    sitecustomize_path = os.path.join(venvdir, 'lib',
                        'python'+sys.version[:3], 'sitecustomize.py')
    if not os.path.exists(sitecustomize_path):
        logger.info("Create sitecustomize.py...")
        with open(sitecustomize_path, 'w') as f:
            f.write("""\
import os, sys, site
sdk_path = os.environ.get('SHEEP_SDK_PATH')
ignore_sdk_path = os.environ.get('SHEEP_IGN_SDKPATH')
if sdk_path and not ignore_sdk_path:
    sdk_site_dir = os.path.join(sdk_path, 'venv', 'lib', 'python'+sys.version[:3],
                    'site-packages')
    site.addsitedir(sdk_site_dir)

    approot = os.environ['SHEEP_APPROOT']
    from sheep.env import activate_app
    activate_app(approot, chdir=False)
""")

    os.environ['SHEEP_APPROOT'] = approot
    os.environ['SHEEP_IGN_SDKPATH'] = 'True'

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

    clear_redundant_pkgs(venvdir)

    if os.path.exists(os.path.join(approot, 'setup.py')):
        logger.info("Running python setup.py develop")
        check_call([os.path.join(venvdir, 'bin', 'python'),
                    os.path.join(approot, 'setup.py'),
                    'develop'])

    logger.info('Sync success...')

def clear_redundant_pkgs(venvdir):
    def _map(line):
        line = line.strip()
        regex = re.compile(r'([-\w]+)@(?:[-\w]+)#egg=(?:[-\w]+)$')
        match = regex.search(line)
        return match.group(1) if match else line

    pip = os.path.join(venvdir, 'bin', 'pip')
    p = Popen([pip, 'freeze'], stdout=PIPE, stderr=PIPE)
    pkgs = set([_map(line) for line in p.stdout])

    reqfile = os.path.join(os.path.dirname(venvdir), 'pip-req.txt')
    if not os.path.isfile(reqfile):
        return

    fobj = open(reqfile)
    req_pkgs = set([_map(line) for line in iter(fobj.readline, '')])
    yes = Popen(['yes'], stdout=PIPE)

    for pkg in pkgs - req_pkgs:
        if pkg.startswith('distribute'):
            continue

        try:
            uninstall = Popen([pip, 'uninstall', pkg], stdin=yes.stdout)
            uninstall.communicate()
            uninstall.wait()
        except:
            logger.exception('uninstall error')

    try:
        yes.terminate()
    except OSError:
        pass

