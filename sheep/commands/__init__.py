#!/usr/bin/python
# encoding: UTF-8

import sys, os
import logging

def main():
    # add the venv/bin/sheep path into $PATH, so that commands like hg,
    # virtualenv, etc. can be found.
    script_path = os.path.realpath(sys.argv[0])
    os.environ['PATH'] = os.path.dirname(script_path) + ':' + os.environ['PATH']

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
        ('sync', 'sync', "Sync workspace"),
        ('log', 'log', "Get log from server"),
        ('dbshell', 'dbshell', "Open shell to control database"),
        ('shell', 'shell', "Open shell for debug online"),
        ('upgrade', 'upgrade', "Upgrade SDK version"),
        ('freeze', 'freeze', "Dump requirements in pip-req.txt"),
    ]
    for command, module_name, help_text in subcommands:
        module = __import__('sheep.commands.'+module_name, globals(), locals(),
                            ['populate_argument_parser', 'main'])

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
    logging.basicConfig(
        level=loglevel,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    return args.func(args)
