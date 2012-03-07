from __future__ import absolute_import

import os, sys
import site
from subprocess import call
import logging

from sheep.util import init_sdk_environ, find_app_root

logger = logging.getLogger(__name__)

def populate_argument_parser(parser):
    parser.add_argument('executable', help="executable under venv/bin/")
    parser.add_argument('arg', nargs='*', help="args passed to the executable")
    parser.epilog = """Insert -- before executable args if they have leading
        dash.  For example: "sheep venv -- python -v"
        """

def main(args):
    approot = find_app_root()
    executable = os.path.join(approot, 'venv', 'bin', args.executable)
    if not os.path.exists(executable):
        logger.error("No such executable: %s", executable)
        return 1

    os.environ['SHEEP_SDK_PATH'] = site.PREFIXES[0]
    init_sdk_environ(approot)
    return call([executable] + args.arg)