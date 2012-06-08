#!/usr/bin/env python
# encoding: UTF-8

"""Script to automatically install SHEEP SDK."""

import sys, os
from subprocess import Popen, PIPE, STDOUT, CalledProcessError
from optparse import OptionParser
from contextlib import contextmanager
import logging

from sheep.libs.colorlog import ColorizingStreamHandler

here = os.path.dirname(__file__)

logging.StreamHandler = ColorizingStreamHandler
logger = logging.getLogger(__name__)

@contextmanager
def chdir(path):
    if path:
        cwd = os.getcwd()
        os.chdir(path)
        yield
        os.chdir(cwd)
    else:
        yield

def log_check_call(*args, **kwargs):
    log = kwargs.pop('log', logging.debug)
    kwargs['stdout'] = PIPE
    kwargs['stderr'] = STDOUT
    kwargs['env'] = env = kwargs.get('env', os.environ.copy())
    env['PYTHONUNBUFFERED'] = '1'
    p = Popen(*args, **kwargs)
    output = []
    for line in iter(p.stdout.readline, ''):
        log(line.rstrip())
        output.append(line)
    retcode = p.wait()
    if retcode != 0:
        cmd = kwargs.get('args') or args[0]
        e = CalledProcessError(retcode, cmd)
        e.output = ''.join(output)
        raise e
    return 0

check_call = log_check_call

def main():
    parser = OptionParser(usage="%prog [options]")
    parser.add_option('-v', '--verbose', action='store_true',
                      help="enable additional output")
    options, args = parser.parse_args()

    loglevel = logging.DEBUG if options.verbose else logging.INFO
    logging.basicConfig(level=loglevel, datefmt="%H:%M:%S",
                        format="%(asctime)s %(message)s")

    try:
        if not check_prerequirements():
            return 1

        install_sheep_sdk()

    except CalledProcessError, e:
        cmd = ' '.join(e.cmd)
        logger.error("Failed when running: %s", cmd)
        if e.output:
            logger.error("Output of the subprocess follows:\n" +
                         e.output.rstrip())

        try:
            send_to_pastebin("Failed when running %s:\n%s" % (cmd, e.output))
        except Exception:
            pass

        return 1

def install_sheep_sdk():
    pkgdir = os.path.abspath(os.path.join(here, '3rdparty'))
    venv = os.path.join(here, 'venv')
    logger.info("Setting up virtualenv...")
    check_call(['python', os.path.join(pkgdir, 'virtualenv.py'),
                '--distribute',
                '--extra-search-dir', pkgdir,
                '--never-download',
                venv])

    bin_dir = os.path.join(venv, 'bin')
    pip_path = os.path.join(bin_dir, 'pip')

    # upgrade to recent version of pip, to ensure --no-install option
    # available
    logger.info("Installing patched pip...")
    wipe = Popen(['yes', 'w'], stdout=PIPE, stderr=open('/dev/null'))
    check_call([pip_path, 'install',
                '-e', 'hg+https://bitbucket.org/CMGS/pip#egg=pip'],
               stdin=wipe.stdout)
    #fixed for osx
    wipe.terminate()

    logger.info("Installing requirements...")

#    install_greenify(venv)

    def log(line):
        if line.startswith("Obtaining ") \
           or line.startswith("Downloading/unpacking ") \
           or line.startswith("Unpacking ") \
           or line.startswith("Installing ") \
           or line.startswith("  Running setup.py install ") \
           or line.startswith("  Running setup.py develop "):
            logger.info(line.rstrip())
        else:
            logger.debug(line.rstrip())

    wipe = Popen(['yes', 'w'], stdout=PIPE, stderr=open('/dev/null'))
    check_call([pip_path, 'install',
                '-r', os.path.join(here, 'requirements.txt'),
                '--find-links', 'file://' + pkgdir,
                '--no-index',
               ], log=log, stdin=wipe.stdout)
    #fixed for osx
    wipe.terminate()

    if sys.version_info < (2, 7):
        check_call([pip_path, 'install', 'argparse==1.2.1',
                    '--find-links', 'file://' + pkgdir,
                    '--no-index',
                   ])

    with chdir(here):
        logger.info("Running setup.py develop for SHEEP SDK...")
        check_call([os.path.join(bin_dir, 'python'), 'setup.py',
                    'develop'])

    prompt_install_symlink(bin_dir)


def prompt_install_symlink(bin_dir):
    bin_path = os.path.abspath(os.path.join(bin_dir, 'sheep'))
    sheep_in_path = which(bin_path)
    if sheep_in_path and os.path.islink(sheep_in_path):
        sheep_in_path = os.path.abspath(os.path.realpath(sheep_in_path))
    if sheep_in_path != bin_path:
        logger.warning("Make a symbolic link to %s in your $PATH, e.g. ", bin_path)
        logger.warning("  ln -s %s $HOME/bin/sheep", bin_path)
        logger.warning("so that you can run `sheep` directly from anywhere :)")


def which(cmd):
    path = os.environ.get('PATH', os.defpath).split(os.pathsep)
    for dir in path:
        if dir: # only non-empty directories are searched
            name = os.path.join(dir, cmd)
            if os.path.exists(name) and os.access(name, os.F_OK|os.X_OK):
                return os.path.abspath(name)

def check_prerequirements():
    for cmd in ['svn', 'git', 'hg', 'cmake', 'make']:
        if not which(cmd):
            logger.error('Command "%s" not found.  Please make sure it is in $PATH.', cmd)
            return False
    return True

def install_greenify(dest_dir):
    logger.info("Obtaining greenify")
    dest_dir = os.path.abspath(dest_dir)
    srcdir = os.path.join(dest_dir, 'src', 'greenify')
    if os.path.exists(srcdir):
        check_call(['git', '--git-dir=%s' % os.path.join(srcdir, '.git'),
                    '--work-tree=%s' % srcdir, 'pull'])
    else:
        check_call(['git', 'clone', 'git://github.com/hongqn/greenify.git',
                    srcdir])

    logger.info("Installing greenify")
    with chdir(srcdir):
        check_call(['cmake', '-G', 'Unix Makefiles',
                    '-D', 'CMAKE_INSTALL_PREFIX=%s' % dest_dir, '.'])
        check_call(['make'])
        check_call(['make', 'install'])

        os.environ['LIBGREENIFY_PREFIX'] = dest_dir
        check_call([os.path.join(dest_dir, 'bin', 'python'), 'setup.py', 'install'])

#def copy_url(url):
#    """Copy the url into the clipboard."""
#    # try windows first
#    try:
#        import win32clipboard
#    except ImportError:
#        # then give pbcopy a try.  do that before gtk because
#        # gtk might be installed on os x but nobody is interested
#        # in the X11 clipboard there.
#        from subprocess import Popen, PIPE
#        for prog in 'pbcopy', 'xclip':
#            try:
#                client = Popen([prog], stdin=PIPE)
#            except OSError:
#                continue
#            else:
#                client.stdin.write(url)
#                client.stdin.close()
#                client.wait()
#                break
#        else:
#            try:
#                import pygtk
#                pygtk.require('2.0')
#                import gtk
#                import gobject
#            except ImportError:
#                return
#            gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD).set_text(url)
#            gobject.idle_add(gtk.main_quit)
#            gtk.main()
#    else:
#        win32clipboard.OpenClipboard()
#        win32clipboard.EmptyClipboard()
#        win32clipboard.SetClipboardText(url)
#        win32clipboard.CloseClipboard()


if __name__ == '__main__':
    sys.exit(main())
