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
import tarfile
from datetime import date, timedelta
import sys
import struct

from osgeo import gdal
from numpy import *

import settings


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

        self.destination = settings.PROCESSED_IMAGES
        self.temp = settings.TEMP_PATH
        self.src_image_path = os.path.join(self.temp, self.image)
        self.b4 = os.path.join(self.src_image_path, self.image + '_B4.TIF')
        self.b5 = os.path.join(self.src_image_path, self.image + '_B5.TIF')
        self.b6 = os.path.join(self.src_image_path, self.image + '_B6.TIF')
        self.delivery_path = os.path.join(self.destination, self.lcpath,
            self.lcrow)

        check_create_folder(self.src_image_path)
        check_create_folder(self.delivery_path)

        self.extract(zip_image, self.src_image_path)

    def full(self):
        '''Make RGB and NDVI and copy BQA image to delivery_path.'''
        self.make_rgb()
        self.make_ndvi()
        self.copy_bqa()
        self.cleanup()

    def extract(self, src, dst):
        '''Extract the Landsat 8 file.'''
        print("Extracting %s - It might take some time" % self.image)
        tar = tarfile.open(src)
        tar.extractall(path=dst)
        tar.close()

    def make_rgb(self):
        '''Make a RGB Image using the bands 4, 5 and 6.'''
        vrt = os.path.join(self.src_image_path, self.image + '.vrt')
        rgb = os.path.join(self.delivery_path, self.new_name + '_r6g5b4.tif')
        call(['gdalbuildvrt', '-q', '-separate', vrt, self.b6, self.b5, self.b4])
        call(['gdal_translate', '-q', '-co', 'COMPRESS=LZW', vrt, rgb])
        print('Created RGB file in %s' % rgb)

    def make_ndvi(self):
        '''Generate a NDVI image.'''

        b4 = gdal.Open(self.b4, gdal.GA_ReadOnly)
        b5 = gdal.Open(self.b5, gdal.GA_ReadOnly)
        if b4 is None or b5 is None:
            print("Some of the datasets could not be opened")
            sys.exit(-1)

        red_band = b4.GetRasterBand(1)
        nir_band = b5.GetRasterBand(1)
        numLines = red_band.YSize

        driver = b4.GetDriver()
        output_file = os.path.join(self.delivery_path, self.new_name + '_ndvi.tif')
        outDataset = driver.Create(output_file, b4.RasterXSize, b4.RasterYSize,
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

            for i in range(len(red_tuple)):
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

        print('NDVI Created in %s' % output_file)

    def copy_bqa(self):
        '''Copy the BQA file to delivery_path.'''
        os.rename(os.path.join(self.src_image_path, self.image + '_BQA.TIF'),
            os.path.join(self.delivery_path, self.new_name + '_BQA.tif'))

    def cleanup(self):
        '''Delete processing image path.'''
        try:
            shutil.rmtree(self.src_image_path)
        except OSError as exc:
            if exc.errno != errno.ENOENT:
                raise