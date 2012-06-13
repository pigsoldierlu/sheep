import os
import sys
import logging
import yaml

from pkg_resources import load_entry_point
from sheep.util import find_app_root, load_dev_config
from sheep.commands.syncdb import sync_database
from sheep.setup import setup_app

TEST_YAML = 'test.yaml'

logger = logging.getLogger(__name__)

def populate_argument_parser(parser):
    parser.add_argument('arg', nargs='*', help="args passed to nosetests")
    parser.epilog = """Insert -- before executable args if they have leading
        dash.  For example: "sheep test -- --help" to get nosetests help
        """


def main(args):
    approot = find_app_root()
    devcfg = load_dev_config(approot)
    if not os.path.exists(os.path.join(approot, TEST_YAML)):
        create_test_yaml(approot, devcfg, TEST_YAML)

    if 'mysql' in devcfg:
        sync_database(approot, 'db_dumps.sql', sync_data=False, remote=False)

    if not os.path.exists(os.path.join(approot, 'permdir_test')):
        os.mkdir(os.path.join(approot, 'permdir_test'))

    os.environ['SHEEP_DEV_YAML'] = TEST_YAML

    nosetests = load_entry_point('nose', 'console_scripts', 'nosetests')
    sys.argv = ['sheep test']
    if os.path.exists(os.path.join(approot, 'nose.cfg')):
        sys.argv += ['-c', os.path.join(approot, 'nose.cfg')]
    sys.argv += args.arg
    setup_app(approot)
    return nosetests()


def create_test_yaml(approot, devcfg, test_yaml):
    logger.warning("Creating %s...", test_yaml)
    if 'mysql' in devcfg:
        devcfg['mysql']['db'] += '_test'
    devcfg['permdir'] = 'permdir_test'
    yaml.safe_dump(devcfg, open(os.path.join(approot, test_yaml), 'w'))
