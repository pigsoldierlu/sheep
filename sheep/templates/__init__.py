#!/usr/bin/python
# encoding: UTF-8

import os
import sys
import getpass
from subprocess import check_call, call

from paste.script.templates import Template, var, NoDefault
from mako.template import Template as MakoTemplate

import sheep.commands.sync
from ..util import validate_appname

def render_mako(content, vars, filename=None):
    return MakoTemplate(text=content, filename=filename).render(**vars)


class MyTemplate(Template):
    template_renderer = staticmethod(render_mako)


class SHEEPTemplate(MyTemplate):
    _template_dir = 'sheep'
    summary = "A Sheep app"
    vars = [
        var('repo_type', "which repo do you want", 'svn'),
        var('repo_url', "url of the project repo", NoDefault),
        var('username', "repo username", getpass.getuser()),
    ]

    def pre(self, command, output_dir, vars):
        vars['appname'] = vars['project']
        validate_appname(vars['project'])

        repo_url = vars['repo_url']
        if command.verbose:
            print "Checking %s" % repo_url

        if vars['repo_type'] == 'svn':
            if call(['svn', 'ls', repo_url]):
                if command.verbose:
                    print "%s not exists. Creating" % repo_url
                check_call(['svn', 'mkdir', repo_url, '-m',
                            "create new project (via sheep create)"])
            check_call(['svn', 'co', repo_url, output_dir])
        elif vars['repo_type'] == 'hg':
            try:
                check_call(['hg', 'clone', repo_url, output_dir])
            except:
                print "You need create repo first."
                sys.exit(0)
        elif vars['repo_type'] == 'git':
            try:
                check_call(['git', 'clone', repo_url, output_dir])
            except:
                print "You need create repo first."
                sys.exit(0)
        else:
            print "You need choose hg or svn or git as project repo."
            sys.exit(0)

    def post(self, command, output_dir, vars):
        #venvdir = os.path.join(output_dir, DEFAULT_VENV_DIR)

        #if command.verbose:
        #    print "Creating virtual environment at %s" % venvdir
        #check_call(['virtualenv', '--no-site-packages', venvdir,
        #            '--prompt', "(%s)" % vars['appname']])

        #if command.verbose:
        #    print "Installing patched pip"
        #check_call([os.path.join(venvdir, 'bin', 'pip'), 'install', '-q',
        #            '-e', 'hg+https://bitbucket.org/CMGS/pip#egg=pip'])

        if command.verbose:
            print "Setting svn:ignore"

        if vars['repo_type'] == 'svn':
            check_call(['svn', 'propset', 'svn:ignore', 'venv\npermdir',
                        output_dir])
            check_call(['svn', 'revert', os.path.join(output_dir, 'permdir')])
        elif vars['repo_type'] == 'hg':
            with open(os.path.join(output_dir, '.hgignore'), 'a') as ignore_file:
                content = "\nsyntax: glob\n\nvenv\npermdir"
                ignore_file.write(content)
            check_call(['hg', 'add', output_dir])
            with open(os.path.join(output_dir, '.hg', 'hgrc'), 'a') as hgrc:
                content = "\n[ui]\nusername = %s\n" % vars['username']
                hgrc.write(content)
        elif vars['repo_type'] == 'git':
            git_dir = os.path.join(output_dir, '.git')
            with open(os.path.join(output_dir, '.gitignore'), 'a') as ignore_file:
                content = "venv\npermdir"
                ignore_file.write(content)
            check_call(['git', '--git-dir', git_dir, '--work-tree', output_dir, 'add', '-A', '.'])
            check_call(['git', '--git-dir', git_dir, '--work-tree', output_dir, 'config', 'user.name', vars['username']])

        class Dummy(object):
            pass
        args = Dummy()
        args.root_path = output_dir
        error = sheep.commands.sync.main(args)
        if error:
            print "Failed to run sheep sync"

        if command.verbose:
            print "Application %s created in %s." % (vars['appname'], output_dir)
            print "Happy hacking!"
