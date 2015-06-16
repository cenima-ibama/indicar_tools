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

from .process import Process


DESCRIPTION = """indicar-tools is the software made by the Indicar Project
to process Landsat imagery.

    Commands:
        Process: creates bands composition, NDVI and a raster change detection
        file containing the losses in the vegetation of the imagery in comparison
        with the NDVI of the same scene generated 16 days ago.
        $ indicar process path

        If you want the change detection as a vector file instead of a raster,
        use the --polygonize parameter:
        $ indicar process path --polygonize

        The default image composition uses the bands 6, 5 and 4. If you want
        use others bands, add the parameter -b or --bands:
        $ indicar process path -b 432

    Options:
        RGB: creates only a RGB image, using the bands 6, 5 and 4. This composition
        gives emphasys to the areas without vegetation.
        $ indicar process --rgb path

        NDVI: creates only a NDVI image. Where there are clouds or cirrus,
        the pixel value will be 0.
        $ indicar process --ndvi path

        Set Directory: by default, indicar-tools will save the processed images
        in a folder named 'landsat' on your home dir, but you can set an
        alternative directory using the --dir parameter.
        $ indicar process path --dir directory_path
"""


def args_options():
    parser = argparse.ArgumentParser(prog='indicar',
                        formatter_class=argparse.RawDescriptionHelpFormatter,
                        description=textwrap.dedent(DESCRIPTION))
    subparsers = parser.add_subparsers(help='Process Utility',
                                       dest='subs')
    parser_process = subparsers.add_parser('process',
                                           help='Process Landsat imagery')
    parser_process.add_argument('path',
                                help="""Path to the compressed Landsat file or to
                                a folder containing the uncompressed files.""")
    parser_process.add_argument('--compose', action='store_true',
                                help='Create only an image composition.')
    parser_process.add_argument('--ndvi', action='store_true',
                                help='Create only a NDVI from the imagery.')
    parser_process.add_argument('--polygonize', action='store_true',
                                help="""When calculating change_detection,
                                polygonize the result generating a geojson file,
                                instead of a TIF image.""")
    parser_process.add_argument('-d', '--dir',
                                help='Directory where the processed images will be stored.')
    parser_process.add_argument('-b', '--bands',
                                help="""Bands that will be used to the image
                                composition. Default value is 654.
                                """)

    return parser


def main(args):
    """Main function - launches the program"""
    if args:
        if args.subs == 'process':
            if args.dir:
                p = Process(args.path, args.dir)
            else:
                p = Process(args.path)
            if args.compose:
                if args.bands:
                    bands = [int(b) for b in args.bands if b.isdigit()]
                    p.make_img(bands)
                else:
                    p.make_img()
            elif args.ndvi:
                p.make_ndvi()
            else:
                if args.bands:
                    bands = [int(b) for b in args.bands if b.isdigit()]
                    p.full(bands, args.polygonize)
                else:
                    p.full(polygonize=args.polygonize)


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
