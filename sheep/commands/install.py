#!/usr/bin/python
# encoding: UTF-8

import os
from subprocess import call, Popen, PIPE
from glob import glob

from sheep.util import find_app_root, get_venvdir, dump_requirements, \
        is_pip_compatible

def populate_argument_parser(parser):
    parser.add_argument('-h', '--help', action='store_true',
                        help="show this help message and exit")
    parser.description = "Must run within app directory."
    parser.epilog = "Delegate to `pip install' in the app's virtual " \
                    "environment.  Usage of `pip install' follows."

def main(args, argv):
    approot = find_app_root()
    venvdir = get_venvdir(approot)
    pip_path = os.path.join(venvdir, 'bin', 'pip')
    os.environ['SHEEP_APPROOT'] = approot

    if args.help:
        print "Usage: sheep install ..."
        print
        print "Delegate to `pip install' in the app's virtual environment."
        print "Must run within app directory."
        print
        print "Usage of `pip install' follows."
        print
        return call([pip_path] + argv)

    if not is_pip_compatible(pip_path):
        return "Your app environment needs to upgrade.  Run 'sheep sync' please."

    pip_download_dir = os.path.join(approot, 'pip-download')
    retval = call([pip_path] + argv + ['--save-download', pip_download_dir])
    dump_requirements(approot)
    if os.path.exists(os.path.join(approot, '.svn')):
        call(['svn', 'add', '-q', pip_download_dir] + \
             glob(os.path.join(pip_download_dir, '*')))
    elif os.path.exists(os.path.join(approot, '.hg')):
        call(['hg', 'add', pip_download_dir])
    return retval


