#!/usr/bin/python
# encoding: UTF-8

import os
import re
import sys
import logging
import tempfile
import threading
import ConfigParser
from cStringIO import StringIO
from subprocess import Popen, PIPE, STDOUT, CalledProcessError, call

import yaml

from .consts import VENV_DIR_KEY, DEFAULT_VENV_DIR

def load_app_config(root_path, replace_macros=True):
    appconf_path = os.path.join(root_path, 'app.yaml')
    appconf = load_config(appconf_path, replace_macros=replace_macros)
    validate_app_conf(appconf)
    return appconf

def load_dev_config(root_path, filename=None):
    if filename is None:
        filename = os.environ.get('SHEEP_DEV_YAML', 'dev.yaml')
    cfgpath = os.path.join(root_path, filename)
    return load_config(cfgpath)

def load_config(path, replace_macros=True):
    py_version = 'python%s.%s' % (sys.version_info[0], sys.version_info[1])
    venv_site_packages = os.path.join('venv', 'lib', py_version,
                                      'site-packages')
    if os.path.exists(path):
        f = open(path)
        if replace_macros:
            f = StringIO(f.read().replace('${VENV_SITE_PACKAGES}', venv_site_packages))
        return yaml.load(f)

    else:
        return {}

def validate_app_conf(appconf):
    """
    >>> validate_app_conf({'application': 'user_registry',
    ...                    'handlers': [{'url': '/', 'wsgi_app': 'wsgi:app'}]})
    >>> validate_app_conf({'application': '1234',
    ...                    'handlers': [{'url': '/', 'wsgi_app': 'wsgi:app'}]})
    Traceback (most recent call last):
        ...
    AssertionError
    >>> validate_app_conf({'application': 'init',
    ...                    'handlers': [{'url': '/', 'wsgi_app': 'wsgi:app'}]})
    Traceback (most recent call last):
        ...
    AssertionError
    """
    appname = appconf['application']
    validate_appname(appname)
    assert appconf['handlers']

def validate_appname(appname):
    """
    >>> validate_appname('user_registry')
    >>> validate_appname('1234')
    Traceback (most recent call last):
        ...
    AssertionError
    >>> validate_appname('init')
    Traceback (most recent call last):
        ...
    AssertionError

    """
    assert re.match(r'[a-z][a-z0-9_]{0,15}$', appname)
    assert not appname in ('init',)

def activate_virtualenv(approot):
    venvdir = get_venvdir(approot)
    if not os.path.exists(venvdir):
        raise Exception("No venv dir found.  Have you run sheep sync before?")

    activate_path = os.path.join(venvdir, 'bin/activate_this.py')
    execfile(activate_path, dict(__file__=activate_path))

    # unload pkg_resources, so that the app can import its own version of
    # pkg_resources from virtual environment.
    if 'pkg_resources' in sys.modules:
        del sys.modules['pkg_resources']

    os.environ['VIRTUAL_ENV'] = venvdir
    os.environ['_OLD_VIRTUAL_PATH'] = os.environ['PATH']
    os.environ['PATH'] = '%s:%s' % (os.path.join(venvdir, 'bin'),
                                    os.environ['PATH'])

def get_venvdir(approot):
    appcfg = load_app_config(approot)
    venvdir = os.path.join(approot,
                           appcfg.get(VENV_DIR_KEY, DEFAULT_VENV_DIR))
    return venvdir

def find_app_root(start_dir=None, raises=True):
    if start_dir is None:
        start_dir = os.getcwd()
    for path in walk_up(start_dir):
        if os.path.exists(os.path.join(path, 'app.yaml')):
            return path

    if raises:
        raise Exception("No app.yaml found in any parent dirs.  Please make sure "
                        "the current working dir is inside the app directory.")
    else:
        return None

def walk_up(dir_):
    while True:
        yield dir_
        olddir, dir_ = dir_, os.path.dirname(dir_)
        if dir_ == olddir:
            break

def log_call(*args, **kwargs):
    log = kwargs.pop('log', logging.debug)
    need_input = kwargs.pop('need_input', False)
    record_output = kwargs.pop('record_output', False)

    if need_input:
        # TODO: use log even if need_input
        if record_output:
            return call(*args, **kwargs), None
        else:
            return call(*args, **kwargs)
    else:
        kwargs['stdin'] = open('/dev/null')

    kwargs['stdout'] = PIPE
    kwargs['stderr'] = STDOUT
    p = Popen(*args, **kwargs)
    output = []
    for line in p.stdout:
        log("%s", line.rstrip())
        if record_output:
            output.append(line)

    if record_output:
        return p.wait(), ''.join(output)
    else:
        return p.wait()

def log_check_call(*args, **kwargs):
    kwargs['record_output'] = True
    retcode, output = log_call(*args, **kwargs)
    if retcode != 0:
        cmd = kwargs.get('args')
        if cmd is None:
            cmd = args[0]
        e = CalledProcessError(retcode, cmd)
        e.output = output
        raise e
    return 0

dev_re = re.compile(r'-dev(_r\d+)?$')
def dump_requirements(approot):
    proj_vcs_url = get_vcs_url(approot)
    p = Popen([os.path.join(get_venvdir(approot), 'bin', 'pip'), 'freeze'],
              stdout=PIPE, stderr=tempfile.TemporaryFile())
    with open(os.path.join(approot, 'pip-req.txt'), 'w') as f:
        for line in p.stdout:
            if proj_vcs_url in line:
                continue
            line = dev_re.sub('', line)
            f.write(line)
    code = p.wait()
    if code:
        raise CalledProcessError(code, 'pip freeze')

def get_vcs_url(approot):
    vcs = get_vcs(approot)
    if vcs == 'hg':
        p = Popen(['hg', '-R', approot, 'showconfig', 'paths.default'],
                  stdout=PIPE)
        remote_url = p.stdout.read().strip()
        p = Popen(['hg', '-R', approot, 'identify', '-i'], stdout=PIPE)
        revision = p.communicate()[0].strip().rstrip('+')

    elif vcs == 'git':
        parser = ConfigParser.ConfigParser()
        content = open(os.path.join(approot, '.git/config')).read()
        config = StringIO('\n'.join(line.strip() for line in content.split('\n')))
        parser.readfp(config)
        remote_url = parser.get('remote "origin"', 'url')

        p = Popen(['git', 'show', '--summary'], stdout=PIPE, cwd=approot)
        revision = p.communicate()[0].split('\n')[0].replace('commit ', '')

    elif vcs == 'svn':
        log_check_call(['svn', 'up'], log=logging.debug)
        env = os.environ.copy()
        env['LC_ALL'] = 'C'
        p = Popen(['svn', 'info', approot], stdout=PIPE, env=env)
        for line in p.stdout:
            if line.startswith('URL: '):
                remote_url = line.split()[1]
            elif line.startswith('Last Changed Rev: '):
                revision = line.split()[3]

    else:
        return None

    return '{0}+{1}@{2}'.format(vcs, remote_url, revision)

def get_vcs(path):
    for vcs in ['hg', 'svn', 'git']:
        if os.path.exists(os.path.join(path, '.'+vcs)):
            return vcs
    return None

def is_pip_compatible(pip_path):
    """Check if `pip --save-download` is supported"""
    stdout, stderr = Popen([pip_path, 'install', '--help'], stdout=PIPE).communicate()
    return '--save-download' in stdout

def init_sdk_environ(approot):
    appconf = load_app_config(approot)

    os.environ['SHEEP_APPROOT'] = approot
    os.environ['SHEEP_RELOAD_MONITOR_DIRS'] = approot
    os.environ['SHEEP_ENV'] = 'SDK'
    os.environ['SHEEP_APPNAME'] = appconf['application']

    if 'PYTHONPATH' not in os.environ:
        os.environ['PYTHONPATH'] = approot
    else:
        os.environ['PYTHONPATH'] = approot + ':' + os.environ['PYTHONPATH']
    sys.path.insert(0, approot)

    activate_virtualenv(approot)

    logging.getLogger('gunicorn').propagate = False

    from sheep.monkey import patch_all
    patch_all(approot)
    os.chdir(approot)

local = None
def get_local():
    global local
    if local is None:
        local = threading.local()
    return local

def set_environ(environ):
    get_local().environ = environ

def get_environ():
    return getattr(get_local(), 'environ', {})
