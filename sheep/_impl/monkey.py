import os
from getpass import getuser

def get_app_mysql_config():
    from sheep.util import load_dev_config
    devcfg = load_dev_config(os.environ['SHEEP_APPROOT']) or {}
    cfg = {
        'host': 'localhost',
        'port': 3306,
        'user': getuser(),
        'passwd': '',
        'db': os.environ['SHEEP_APPNAME'],
    }
    cfg.update(devcfg.get('mysql', {}))
    return cfg

def patch_impl():
    pass

def patch_log():
    pass
