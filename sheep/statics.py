#!/usr/bin/python
# encoding: UTF-8

import os
import json
import urllib2
import logging

from .util import find_app_root, load_app_config

DEFAULT_SERVER = 'http://deploy.xiaom.co'

logger = logging.getLogger(__name__)

def populate_argument_parser(parser):
    parser.add_argument('root_path', metavar='<app root>', nargs='?',
                      help="directory contains app.yaml "
                           "[default: find automatically in parent dirs]")
    parser.add_argument('-s', '--server', default=DEFAULT_SERVER,
                        help="The AppEngine deploy server [default: %s]" % DEFAULT_SERVER)

def main(args):
    root_path = args.root_path or find_app_root()
    mirror_statics(root_path, server=args.server)

def mirror_statics(root_path, server):
    appcfg = load_app_config(root_path)
    statics = []
    for handler_config in appcfg['handlers']:
        if 'static_files' not in handler_config:
            continue
        statics.append(handler_config)
    if not statics:
        logger.info("No Statics configuration found.")
        return 'Mirror succeeded.'

    logger.info("Mirror static files to UpYun...")
    post_data = json.dumps({'application': appcfg['application'], 'configs': statics})
    post_url = '%s/statics/' % server
    verbose = logger.getEffectiveLevel()

    req = urllib2.Request(post_url, post_data)
    f = urllib2.urlopen(req)
    line = ''
    for line in iter(f.readline, ''):
        try:
            loglevel, line = line.split(':', 1)
            loglevel = int(loglevel)
        except ValueError:
            loglevel = logging.DEBUG
        if loglevel >= verbose:
            logger.log(loglevel, "%s", line.rstrip())
    return line
