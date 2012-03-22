#!/usr/bin/python
# encoding: UTF-8

import os
import sys
import yaml
import logging

from pkg_resources import load_entry_point
from sheep.util import init_sdk_environ, find_app_root, load_dev_config

TEST_YAML = 'test.yaml'

logger = logging.getLogger(__name__)

def populate_argument_parser(parser):
    parser.add_argument('arg', nargs='*', help="args passed to nosetests")
    parser.epilog = """Insert -- before executable args if they have leading
        dash.  For example: "sheep test -- --help" to get nosetests help
        """


def main(args):
    approot = find_app_root()
    if not os.path.exists(os.path.join(approot, TEST_YAML)):
        create_test_yaml(approot, TEST_YAML)
    os.environ['SHEEP_DEV_YAML'] = TEST_YAML

    init_sdk_environ(approot)
    nosetests = load_entry_point('nose', 'console_scripts', 'nosetests')
    sys.argv = ['sheep test']
    if os.path.exists(os.path.join(approot, 'nose.cfg')):
        sys.argv += ['-c', os.path.join(approot, 'nose.cfg')]
    sys.argv += args.arg
    return nosetests()


def create_test_yaml(approot, test_yaml):
    logger.warning("Creating %s...", test_yaml)
    devcfg = load_dev_config(approot)
    if 'mysql' in devcfg:
        devcfg['mysql']['db'] += '_test'
    devcfg['permdir'] = 'permdir_test'
    yaml.safe_dump(devcfg, open(os.path.join(approot, test_yaml), 'w'))

