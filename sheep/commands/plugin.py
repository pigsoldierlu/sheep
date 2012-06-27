#!/usr/bin/python
# encoding: UTF-8

import os
import logging
from subprocess import call

logger = logging.getLogger(__name__)

def populate_argument_parser(parser):
    parser.add_argument('setup_file', const=str, nargs='?', default='setup.py')
    parser.add_argument('action')

def main(args):
    if args.action not in ['install', 'develop']:
        logger.error('action error')
        return 0

    python_path = os.path.join(os.environ['SHEEP_SDK_PATH'], 'venv', 'bin', 'python')
    retval = call([python_path, args.setup_file, args.action])
    return retval

class PluginCommand(object):
    def run(self):
        raise NotImplementedError

