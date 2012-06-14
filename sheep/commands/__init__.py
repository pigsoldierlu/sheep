#!/usr/bin/python
# encoding: UTF-8

import sys
import logging
import pkg_resources

from sheep.env import init
from sheep.libs.colorlog import ColorizingStreamHandler

def main():
    init()

    from argparse import ArgumentParser
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(title="commands",
                                       dest='subparser_command')
    subcommands = [
        ('create', 'create', "Create a new Sheep app"),
        ('serve', 'dev_appserver', "Run develop server"),
        ('install', 'install', "Install dependencies"),
        ('uninstall', 'uninstall', "Uninstall dependencies"),
        ('deploy', 'deploy', "Deploy application"),
        ('syncdb', 'syncdb', "Sync database"),
        ('mirror', 'statics', "Mirror statics"),
        ('venv', 'venv', "Run executables under venv/bin/"),
        ('test', 'test', "Run tests"),
        ('sync', 'sync', "Sync workspace"),
        ('log', 'log', "Get log from server"),
        ('dbshell', 'dbshell', "Open shell to control database"),
        ('shell', 'shell', "Open shell for debug online"),
        ('upgrade', 'upgrade', "Upgrade SDK version"),
        ('freeze', 'freeze', "Dump requirements in pip-req.txt"),
    ]

    if len(sys.argv) > 1:
        from sheep.commands.plugin import PluginCommand
        subcmd = sys.argv[1]
        if subcmd not in [sc[0] for sc in subcommands]:
            for ep in pkg_resources.iter_entry_points('sheep.plugins', name=subcmd):
                try:
                    klass = ep.load()
                except ImportError:
                    pass
                else:
                    if getattr(klass, '__base__', None) is PluginCommand:
                        sys.exit(klass().run())
                    else:
                        raise Exception('%s must be a child-class of '
                                        'sheep.commands.plugin.PluginCommand' %
                                        klass)

    for command, module_name, help_text in subcommands:
        try:
            module = __import__('sheep.commands.'+module_name, globals(), locals(),
                                ['populate_argument_parser', 'main'])
        except ImportError:
            import traceback; traceback.print_exc()
            print >>sys.stderr, "Can not import command %s, skip it" % command
            continue

        if command in ('install', 'uninstall'):
            subparser = subparsers.add_parser(command, help=help_text,
                                              add_help=False)
        else:
            subparser = subparsers.add_parser(command, help=help_text)
            subparser.add_argument('-v', '--verbose', action='store_true',
                                    help="enable additional output")

        module.populate_argument_parser(subparser)
        subparser.set_defaults(func=module.main)

    argv = sys.argv[1:] or ['--help']
    args, _ = parser.parse_known_args(argv)
    if args.subparser_command in ('install', 'uninstall'):
        # sheep install is a delegator for pip install/uninstall
        return args.func(args, argv)

    args = parser.parse_args(argv)

    if args.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO

    logging.StreamHandler = ColorizingStreamHandler
    logging.BASIC_FORMAT = "%(asctime)s [%(name)s] %(message)s"
    logging.basicConfig(level=loglevel)

    return args.func(args)
