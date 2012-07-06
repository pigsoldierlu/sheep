# encoding: UTF-8

"""
setup 操作有两类，影响SHEEP启动代码的(init)，和影响app代码的(setup)。 影响SHEEP启
动代码的应尽早执行（比如main函数），影响应用代码的应尽晚执行（但在应用代码执行
前）。
"""

import os, sys
import logging

import sheep._impl.env as _impl

from .util import load_app_config, get_venvdir

__all__ = ['init', 'init_app', 'activate_app']

def init():
    """初始化SHEEP代码需要的环境"""
    _impl.init()
    logging.getLogger('gunicorn').propagate = False


def init_app(approot):
    init()
    os.environ['SHEEP_APPROOT'] = os.path.abspath(approot)
    appcfg = load_app_config(approot)
    os.environ['SHEEP_APPNAME'] = appcfg['application']
    os.environ['SHEEP_WORKER'] = appcfg.get('worker', 'async')

def activate_app(approot, chdir=True):
    """配置应用代码运行环境"""

    approot = os.path.abspath(approot)
    init_app(approot)

    import sheep.monkey
    sheep.monkey.patch_all(approot)

    os.chdir(approot)
    activate_virtualenv(approot)
    sys.path.insert(0, approot)

    _impl.activate_app()

    if chdir:
        os.chdir(approot)

def activate_virtualenv(approot):
    venvdir = os.path.abspath(get_venvdir(approot))
    if not os.path.exists(venvdir):
        raise Exception("No venv dir found.  Have you run sheep sync before?")

    # unload pkg_resources, so that the app can import its own version of
    # pkg_resources from virtual environment.
    if 'pkg_resources' in sys.modules:
        del sys.modules['pkg_resources']

    activate_path = os.path.join(venvdir, 'bin/activate_this.py')
    execfile(activate_path, dict(__file__=activate_path))

    os.environ['VIRTUAL_ENV'] = venvdir
    os.environ['_OLD_VIRTUAL_PATH'] = os.environ['PATH']
    os.environ['PATH'] = '%s:%s' % (os.path.join(venvdir, 'bin'),
                                    os.environ['PATH'])

    sys.prefix = sys.exec_prefix = venvdir
    if 'distutils.sysconfig' in sys.modules:
        del sys.modules['distutils.sysconfig']

    # Recalculate namespace packages' __path__ attribute
    import pkg_resources
