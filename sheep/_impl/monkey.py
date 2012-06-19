import os

def get_app_mysql_config():
    from sheep.util import load_dev_config
    devcfg = load_dev_config(os.environ['SHEEP_APPROOT']) or {}
    return devcfg.get('mysql', {})

def patch_impl():
    pass

def patch_log():
    pass
