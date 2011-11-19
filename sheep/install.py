#!/usr/bin/python
# encoding: UTF-8

import os
from subprocess import call, Popen, PIPE
from glob import glob

from .util import find_app_root, get_venvdir, dump_requirements, \
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

    call(['mkdir', '-p', os.path.join(approot, 'pip-download')])
    retval = call([pip_path] + argv + ['--download',
                                       os.path.join(approot, 'pip-download')])
    dump_requirements(approot)
    if os.path.exists(os.path.join(approot, '.svn')):
        call(['svn', 'add', '-q', os.path.join(approot, 'pip-download')] + \
             glob(os.path.join(approot, 'pip-download', '*')))
    elif os.path.exists(os.path.join(approot, '.hg')):
        call(['hg', 'add', os.path.join(approot, 'pip-download')] + \
             glob(os.path.join(approot, 'pip-download', '*')))
    return retval


