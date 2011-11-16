#!/usr/bin/python
# encoding: UTF-8

from subprocess import call

def populate_argument_parser(parser):
    parser.add_argument('appname', help="the unique app name")
    parser.add_argument('--dir', nargs='?',
                        help="directory to put the app "
                             "[default: the current directory]")
    parser.add_argument('--port', nargs='?', type=int,
                        help="unique port number [default: ask]")
    parser.add_argument('--uid', nargs='?', type=int,
                        help="unique uid to run the app [default: ask]")
    parser.add_argument('--repo-url', nargs='?',
                        help="svn url of the project [default: ask]")

def main(args):
    cmd = ['paster', 'create', '-t', 'sheep']
    if args.dir:
        cmd += ['-o', args.dir]
    cmd += [args.appname]
    if args.port:
        cmd += ['port=%s' % args.port]
    if args.uid:
        cmd += ['uid=%s' % args.uid]
    if args.repo_url:
        cmd += ['repo_url=%s' % args.repo_url]
    return call(cmd)
