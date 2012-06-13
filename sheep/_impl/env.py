# encoding: UTF-8

import os
import pkg_resources

def init():
    dist = pkg_resources.get_distribution('sheep')
    os.environ['SHEEP_ENV'] = 'SDK'
    os.environ['SHEEP_ENV_VERSION'] = dist.version
    os.environ['SHEEP_SDK_PATH'] = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def activate_app():
    # entry point for farm._impl
    pass
