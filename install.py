#!/usr/bin/python
# encoding: UTF-8

"""Script to automatically install Sheep SDK."""

import sys, os
from subprocess import check_call, Popen, PIPE, CalledProcessError
from optparse import OptionParser
import shutil
from contextlib import contextmanager
import urllib

GREEN = '\x1b[01;32m'
NORMAL = '\x1b[0m'
PIP_VERSION = '1.0.2'
GEVENT_VERSION = '0.13.6'

@contextmanager
def chdir(path):
    cwd = os.getcwd()
    os.chdir(path)
    yield
    os.chdir(cwd)

def main():
    parser = OptionParser(usage="%prog [options] [dir]")
    parser.add_option('--revision', type='int',
                      help="Update to a specific revision of SDK [default: HEAD]")
    parser.add_option('--sdk-src',
                      help="Use the checked out source code (debug purpose only)")
    options, args = parser.parse_args()
    dest_dir = args[0] if args else 'sheep'
    dest_dir = os.path.abspath(dest_dir)

    # Sheep SDK needs svn and hg commands in PATH
    if not which('svn'):
        return "Command svn not found.  Please install subversion and " \
                "make sure svn is in $PATH."
    if not check_prerequirements():
        return 1

    if not os.path.exists(dest_dir):
        os.mkdir(dest_dir)

    install_sheep_sdk(dest_dir, revision=options.revision, \
            sdk_src_dir=options.sdk_src)


def install_sheep_sdk(dest_dir, revision=None, sdk_src_dir=None):
    src_dir = os.path.join(dest_dir, 'sdk')

    if sdk_src_dir:
        shutil.copytree(sdk_src_dir, src_dir)
    else:
        cmd = ['svn', 'co', 'http://ursa.googlecode.com/svn/sheep-farm/sheep',
               src_dir]
        if revision is not None:
            cmd += ['-r', str(revision)]
        check_call(cmd)

    pkgdir = os.path.abspath(os.path.join(src_dir, '3rdparty'))

    check_call(['python', os.path.join(pkgdir, 'virtualenv.py'),
                '--no-site-packages', '--distribute',
                '--extra-search-dir', pkgdir,
                '--never-download',
                dest_dir])

    bin_dir = os.path.join(dest_dir, 'bin')
    pip_path = os.path.join(bin_dir, 'pip')

    # upgrade to recent version of pip, to ensure --no-install option
    # available
    check_call([pip_path, 'install',
                os.path.join(pkgdir, 'pip-%s.tar.gz' % PIP_VERSION)])

    install_libgreenify(dest_dir)

    check_call([pip_path, 'install',
                '-r', os.path.join(src_dir, 'requirements.txt'),
                '--find-links', 'file://' + pkgdir,
                '--no-index',
               ])

    if sys.version_info < (2, 7):
        check_call([pip_path, 'install', 'argparse==1.2.1',
                    '--find-links', 'file://' + pkgdir,
                    '--no-index',
                   ])

    with chdir(src_dir):
        check_call([os.path.join(bin_dir, 'python'), 'setup.py',
                    'develop'])

    print
    print
    sys.stdout.write(GREEN)
    print "Make a symbolic link to %s in your $PATH, e.g. /usr/local/bin " \
            "so that you can run `sheep` directly from anywhere :)" \
            % os.path.abspath(os.path.join(bin_dir, 'sheep'))
    sys.stdout.write(NORMAL)


def which(cmd):
    path = os.environ.get('PATH', os.defpath).split(os.pathsep)
    for dir in path:
        if dir: # only non-empty directories are searched
            name = os.path.join(dir, cmd)
            if os.path.exists(name) and os.access(name, os.F_OK|os.X_OK):
                return name

def check_prerequirements():
    for cmd in ['svn', 'git', 'cmake', 'make']:
        if not which(cmd):
            print 'Command "%s" not found.  Please make sure it is in $PATH.' % cmd
            return False
    return True

def install_libgreenify(dest_dir):
    srcdir = os.path.join(dest_dir, 'src', 'greenify')
    if os.path.exists(srcdir):
        check_call(['git', '--git-dir=%s' % os.path.join(srcdir, '.git'),
                    '--work-tree=%s' % srcdir, 'pull'])
    else:
        check_call(['git', 'clone', 'git://github.com/hongqn/greenify.git',
                    srcdir])

    with chdir(srcdir):
        check_call(['cmake', '-G', 'Unix Makefiles',
                    '-D', 'CMAKE_INSTALL_PREFIX=%s' % dest_dir, '.'])
        check_call(['make'])
        check_call(['make', 'install'])

        os.environ['LIBGREENIFY_PREFIX'] = dest_dir
        check_call([os.path.join(dest_dir, 'bin', 'python'), 'setup.py', 'install'])

if __name__ == '__main__':
    sys.exit(main())
