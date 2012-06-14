# encoding: UTF-8

import os
import pkg_resources

def init():
    os.environ['SHEEP_ENV'] = 'SDK'
    try:
        dist = pkg_resources.get_distribution('sheep')
        os.environ['SHEEP_ENV_VERSION'] = dist.version
    except Exception:
        os.environ['SHEEP_ENV_VERSION'] = 'unknown'

    os.environ['SHEEP_SDK_PATH'] = os.path.abspath(
            os.path.dirname(                        # sheep/
                os.path.dirname(                    # sheep/sheep/
                    os.path.dirname(__file__))))    # sheep/sheep/_impl/


def activate_app():
    # entry point for farm._impl
    pass
