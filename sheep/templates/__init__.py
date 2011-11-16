#!/usr/bin/python
# encoding: UTF-8

import os
from subprocess import check_call, call

from paste.script.templates import Template, var, NoDefault
from mako.template import Template as MakoTemplate

from ..util import validate_appname
from ..consts import DEFAULT_VENV_DIR

def render_mako(content, vars, filename=None):
    return MakoTemplate(text=content, filename=filename).render(**vars)


class MyTemplate(Template):
    template_renderer = staticmethod(render_mako)


class SHEEPTemplate(MyTemplate):
    _template_dir = 'sheep'
    summary = "A Sheep app"
    vars = [
        var('repo_url', "svn url of the project", NoDefault),
    ]

    def pre(self, command, output_dir, vars):
        vars['appname'] = vars['project']
        validate_appname(vars['project'])

        repo_url = vars['repo_url']
        if command.verbose:
            print "Checking %s" % repo_url
        if call(['svn', 'ls', repo_url]):
            if command.verbose:
                print "%s not exists. Creating" % repo_url
            check_call(['svn', 'mkdir', repo_url, '-m',
                        "create new project (via sheep create)"])
        if command.verbose:
            print "Checking out %s" % repo_url
        check_call(['svn', 'co', repo_url, output_dir])

    def post(self, command, output_dir, vars):
        venvdir = os.path.join(output_dir, DEFAULT_VENV_DIR)

        if command.verbose:
            print "Creating virtual environment at %s" % venvdir
        check_call(['virtualenv', '--no-site-packages', venvdir,
                    '--prompt', "(%s)" % vars['appname']])

        #if command.verbose:
        #    print "Installing patched pip"
        #check_call([os.path.join(venvdir, 'bin', 'pip'), 'install', '-q',
        #            '-e', 'hg+http://shire:hobbits@hg.douban.com/pip#egg=pip'])

        if command.verbose:
            print "Setting svn:ignore"
            check_call(['svn', 'propset', 'svn:ignore', 'venv\npermdir',
                        output_dir])
            # paster add all template-generated files to vcs, but we do not
            # want to checkin permdir
            check_call(['svn', 'revert', os.path.join(output_dir, 'permdir')])

        if command.verbose:
            print "Application %s created in %s." % (vars['appname'], output_dir)
            print "RTFM http://goo.gl/jODG2 and happy hacking!"
