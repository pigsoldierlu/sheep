from sheep.util import dump_requirements, find_app_root

def populate_argument_parser(parser):
    pass

def main(args):
    approot = find_app_root()
    dump_requirements(approot)
