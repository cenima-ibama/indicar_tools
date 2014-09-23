#!/usr/bin/env python

# Indicar Landsat Geoprocessing Tools
#
#
# Author: Hex Gis
# Contributor: willemarcel
#
# License: GPLv3

from __future__ import print_function
import argparse
import textwrap
import sys

import settings
from process import Process


DESCRIPTION = """Indicar tools is the software made by the Indicar Project
to process Landsat 8 imagery.

    Commands:
        Process: creates RGB images and NDVI from a scene imagery
        indicar.py process path

        Rgb:  creates only a RGB image
        indicar.py process --only-rgb path

        Ndvi: creates only a NDVI image
        indicar.py process --only-ndvi path
"""


def args_options():
    parser = argparse.ArgumentParser(prog='indicar.py',
                        formatter_class=argparse.RawDescriptionHelpFormatter,
                        description=textwrap.dedent(DESCRIPTION))
    subparsers = parser.add_subparsers(help='Process Utility',
                                       dest='subs')
    parser_process = subparsers.add_parser('process',
                                           help='Process Landsat 8 imagery')
    parser_process.add_argument('path',
                                help='Path to the compressed image file')
    parser_process.add_argument('--rgb', action='store_true',
                                help='Create only a RGB from the imagery')
    parser_process.add_argument('--ndvi', action='store_true',
                                help='Create only a NDVI from the imagery')

    return parser


def main(args):
    """
    Main function - launches the program
    """
    if args:
        if args.subs == 'process':
            p = Process(args.path)
            if args.rgb:
                p.make_rgb()
                p.cleanup()
                exit("The output is stored at %s." % settings.PROCESSED_IMAGES)
            elif args.ndvi:
                p.make_ndvi()
                p.cleanup()
            else:
                p.full()
            exit("The output is stored at %s." % settings.PROCESSED_IMAGES)


def exit(message, code=0):
    print(message)
    sys.exit(code)


def __main__():

    global parser
    parser = args_options()
    args = parser.parse_args()
    main(args)

if __name__ == "__main__":
    __main__()