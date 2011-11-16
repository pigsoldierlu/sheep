import os
from subprocess import call

from .util import find_app_root, get_venvdir, dump_requirements

def populate_argument_parser(parser):
    parser.add_argument('-h', '--help', action='store_true',
                        help="show this help message and exit")
    parser.description = "Must run within app directory."
    parser.epilog = "Delegate to `pip uninstall' in the app's virtual " \
                    "environment.  Usage of `pip uninstall' follows."

def main(args, argv):
    approot = find_app_root()
    venvdir = get_venvdir(approot)
    if args.help:
        print "Usage: sheep uninstall ..."
        print
        print "Delegate to `pip uninstall' in the app's virtual environment."
        print "Must run within app directory."
        print
        print "Usage of `pip install' follows."
        print
    retval = call([os.path.join(venvdir, 'bin', 'pip')] + argv)
    dump_requirements(approot)
    return retval


