# Indicar Landsat Geoprocessing Tools
#
#
# Author: Hex Gis
# Contributor: willemarcel
#
# License: GPLv3

from __future__ import print_function
import os
from subprocess import call
import errno
import shutil
from datetime import date, timedelta
import sys
import struct

from osgeo import gdal
from numpy import *

import settings
from gdal_operations import *


def check_create_folder(folder_path):
    """ Check whether a folder exists, if not the folder is created
    Always return folder_path
    """
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print("%s folder created" % folder_path)

    return folder_path


def get_file(path):
    """ Separate the name of the file or folder from the path and return it
    Example: /path/to/file ---> file
    """
    return os.path.basename(path)


def get_image_bounds(image_path):
    """ Return the coordinates of the lower left (minx, miny) and the
    upper right (maxx, maxy) of the image. """
    ds = gdal.Open(image_path, gdal.GA_ReadOnly)
    width = ds.RasterXSize
    height = ds.RasterYSize
    gt = ds.GetGeoTransform()
    minx = gt[0]
    miny = gt[3] + width * gt[4] + height * gt[5]
    maxx = gt[0] + width * gt[1] + height * gt[2]
    maxy = gt[3]

    return ((minx, miny), (maxx, maxy))


def get_intersection_bounds(image1, image2):
    """ Return the intersection bounds of 2 images. The method used is to get
    the max value of the minx and miny and the minimum value of maxx and maxy"""
    img1_bounds = get_image_bounds(image1)
    img2_bounds = get_image_bounds(image2)

    minx = [img1_bounds[0][0], img2_bounds[0][0]]
    minx.sort()
    miny = [img1_bounds[0][1], img2_bounds[0][1]]
    miny.sort()
    maxx = [img1_bounds[1][0], img2_bounds[1][0]]
    maxx.sort()
    maxy = [img1_bounds[1][1], img2_bounds[1][1]]
    maxy.sort()

    return [minx[1], miny[1], maxx[0], maxy[0]]


class Process(object):

    def __init__(self, zip_image):
        """ Initating the Process class

        Arguments:
        zip_image - the string containing the path of the landsat 8 compressed file

        """
        self.image = get_file(zip_image).split('.')[0]
        self.lcpath = self.image[3:6]
        self.lcrow = self.image[6:9]
        self.year = self.image[9:13]
        self.day = self.image[13:16]
        self.date = (date(int(self.year), 1, 1) + timedelta(int(self.day) - 1)
                    ).strftime('%Y%m%d')
        self.new_name = "%s_%s-%s_%s_%s" % (self.image[:3], self.lcpath,
            self.lcrow, self.date, self.image[16:])

        # date of last image of the scene
        self.last_date = (date(int(self.year), 1, 1) + \
                    timedelta(int(self.day) - 17)
                    ).strftime('%Y%m%d')
        # name of last image of the scene
        self.last_image = "%s_%s-%s_%s_%s" % (self.image[:3], self.lcpath,
            self.lcrow, self.last_date, self.image[16:])

        self.destination = settings.PROCESSED_IMAGES
        self.temp = settings.TEMP_PATH
        self.src_image_path = os.path.join(self.temp, self.image)
        self.b4 = os.path.join(self.src_image_path, self.image + '_B4.TIF')
        self.b5 = os.path.join(self.src_image_path, self.image + '_B5.TIF')
        self.b6 = os.path.join(self.src_image_path, self.image + '_B6.TIF')
        self.bqa = os.path.join(self.src_image_path, self.image + '_BQA.TIF')
        self.delivery_path = os.path.join(self.destination, self.lcpath,
            self.lcrow)
        self.ndvi = os.path.join(self.delivery_path, self.new_name + '_ndvi.tif')

        check_create_folder(self.src_image_path)
        check_create_folder(self.delivery_path)

        self.extract(zip_image, self.src_image_path)

    def full(self):
        '''Make RGB and NDVI and move BQA image to delivery_path.'''
        self.make_rgb()
        self.make_ndvi()
        self.move_bqa()
        self.change_detection()
        self.cleanup()

    def extract(self, src, dst):
        '''Extract the Landsat 8 file.'''
        print("Extracting %s - It might take some time" % self.image)
        call(['tar', '-xzf', src, '-C', dst])

    def make_rgb(self):
        '''Make a RGB Image using the bands 4, 5 and 6.'''
        vrt = os.path.join(self.src_image_path, self.image + '.vrt')
        rgb = os.path.join(self.delivery_path, self.new_name + '_r6g5b4.tif')
        call(['gdalbuildvrt', '-q', '-separate', vrt, self.b6, self.b5, self.b4])
        call(['gdal_translate', '-q', '-co', 'COMPRESS=LZW', vrt, rgb])
        print('Created RGB file in %s' % rgb)

    def make_ndvi(self):
        '''Generate a NDVI image. If the BQA value indicates cloud or cirrus,
        the NDVI value will be zero.'''

        b4 = gdal.Open(self.b4, gdal.GA_ReadOnly)
        b5 = gdal.Open(self.b5, gdal.GA_ReadOnly)
        bqa = gdal.Open(self.bqa, gdal.GA_ReadOnly)

        if b4 is None or b5 is None or bqa is None:
            print("Some of the datasets could not be opened")
            sys.exit(-1)

        red_band = b4.GetRasterBand(1)
        nir_band = b5.GetRasterBand(1)
        bqa_band = bqa.GetRasterBand(1)
        numLines = red_band.YSize

        bqa_values = [61440, 59424, 57344, 56320, 53248, 52256, 52224, 49184,
            49152, 48128, 45056, 43040, 39936, 36896, 36864, 32768, 31744, 28672]

        driver = b4.GetDriver()
        outDataset = driver.Create(self.ndvi, b4.RasterXSize, b4.RasterYSize,
            1, gdal.GDT_Float32)
        outDataset.SetGeoTransform(b4.GetGeoTransform())
        outDataset.SetProjection(b4.GetProjection())

        if outDataset is None:
            print('Could not create output image')
            sys.exit(-1)

        for line in range(numLines):
            outputLine = ''
            red_scanline = red_band.ReadRaster(0, line, red_band.XSize, 1,
                red_band.XSize, 1, gdal.GDT_Float32)
            red_tuple = struct.unpack('f' * red_band.XSize, red_scanline)

            nir_scanline = nir_band.ReadRaster(0, line, nir_band.XSize, 1,
                nir_band.XSize, 1, gdal.GDT_Float32)
            nir_tuple = struct.unpack('f' * nir_band.XSize, nir_scanline)

            bqa_scanline = bqa_band.ReadRaster(0, line, bqa_band.XSize, 1,
                bqa_band.XSize, 1, gdal.GDT_Float32)
            bqa_tuple = struct.unpack('f' * bqa_band.XSize, bqa_scanline)

            for i in range(len(red_tuple)):
                if bqa_tuple[i] in bqa_values:
                    ndvi = 0
                else:
                    ndvi_lower = (nir_tuple[i] + red_tuple[i])
                    ndvi_upper = (nir_tuple[i] - red_tuple[i])
                    ndvi = 0
                    if ndvi_lower == 0:
                        ndvi = 0
                    else:
                        ndvi = ndvi_upper / ndvi_lower

                outputLine = outputLine + struct.pack('f', ndvi)

            outDataset.GetRasterBand(1).WriteRaster(0, line, red_band.XSize, 1,
                outputLine, buf_xsize=red_band.XSize, buf_ysize=1,
                buf_type=gdal.GDT_Float32)
            del outputLine

        print('NDVI Created in %s' % self.ndvi)

    def change_detection(self):
        ndvi_warp = os.path.join(self.src_image_path,
            self.new_name + '_ndvi_warp.tif')
        last_ndvi = os.path.join(self.delivery_path,
            self.last_image + '_ndvi.tif')
        last_ndvi_warp = os.path.join(self.src_image_path,
            self.last_image + '_ndviwarp.tif')
        changes = os.path.join(self.src_image_path,
            self.new_name + '_changes.tif')
        changes_mask = os.path.join(self.src_image_path,
            self.new_name + '_changes_mask.tif')
        sieve = os.path.join(self.src_image_path,
            self.new_name + '_sieve.tif')
        detection = os.path.join(self.delivery_path,
            self.new_name + '_detection.gml')
        if os.path.isfile(self.ndvi) and os.path.isfile(last_ndvi):
            if get_image_bounds(self.ndvi) != get_image_bounds(last_ndvi):
                bounds = get_intersection_bounds(self.ndvi, last_ndvi)
                warp_image(self.ndvi, bounds, ndvi_warp)
                warp_image(last_ndvi, bounds, last_ndvi_warp)
                subtract(ndvi_warp, last_ndvi_warp, changes)
            else:
                subtract(self.ndvi, last_ndvi, changes)

            mask_image(changes, -0.1, changes_mask)
            call(['gdal_sieve.py', '-st', '-25', changes_mask, sieve])
            call(['gdal_polygonize.py', sieve, detection])
            print('Change detection created in %s.' % detection)
        else:
            print('Change detection was not executed because some NDVI image is missing.')

    def move_bqa(self):
        '''Move the BQA file to delivery_path.'''
        if os.path.isfile(self.bqa):
            os.rename(self.bqa,
                os.path.join(self.delivery_path, self.new_name + '_BQA.tif'))
        else:
            print('BQA file not found')

    def cleanup(self):
        '''Delete processing image path.'''
        try:
            shutil.rmtree(self.src_image_path)
        except OSError as exc:
            if exc.errno != errno.ENOENT:
                raise