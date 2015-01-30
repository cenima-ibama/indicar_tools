# Indicar Landsat Geoprocessing Tools
#
#
# Author: Hex Gis
# Contributor: willemarcel
#
# License: GPLv3

from __future__ import print_function
from subprocess import call
import struct
import sys

from osgeo import gdal


def warp_image(image, bounds, output_file):
    """Warp image to the boundaries coordinates."""
    bounds = ['%s' % i for i in bounds]
    call(['gdalwarp', '-te'] + bounds + [image, output_file])
    print('Warp image created in %s' % output_file)


def subtract(img1, img2, output_file):
    """Subtract the img2 from img1. If the pixel value of any
    image is zero, the result of the subtraction will be zero.
    """
    image1 = gdal.Open(img1, gdal.GA_ReadOnly)
    image2 = gdal.Open(img2, gdal.GA_ReadOnly)

    if image1 is None or image2 is None:
        print('Some of the datasets could not be opened')
        sys.exit(-1)

    img1_band = image1.GetRasterBand(1)
    img2_band = image2.GetRasterBand(1)
    numLines = img1_band.YSize

    driver = image1.GetDriver()
    outDataset = driver.Create(output_file, image1.RasterXSize,
        image1.RasterYSize, 1, gdal.GDT_Float32)
    outDataset.SetGeoTransform(image1.GetGeoTransform())
    outDataset.SetProjection(image1.GetProjection())

    if outDataset is None:
        print('Could not create output image')
        sys.exit(-1)

    for line in range(numLines):
        outputLine = ''
        img1_scanline = img1_band.ReadRaster(0, line, img1_band.XSize, 1,
            img1_band.XSize, 1, gdal.GDT_Float32)
        img1_tuple = struct.unpack('f' * img1_band.XSize, img1_scanline)

        img2_scanline = img2_band.ReadRaster(0, line, img2_band.XSize, 1,
            img2_band.XSize, 1, gdal.GDT_Float32)
        img2_tuple = struct.unpack('f' * img2_band.XSize, img2_scanline)

        for i in range(len(img1_tuple)):
            if img1_tuple[i] == 0 or img2_tuple[i] == 0:
                result = 0
            else:
                result = img1_tuple[i] - img2_tuple[i]

            outputLine = outputLine + struct.pack('f', result)

        outDataset.GetRasterBand(1).WriteRaster(0, line, img1_band.XSize, 1,
            outputLine, buf_xsize=img1_band.XSize, buf_ysize=1,
            buf_type=gdal.GDT_Float32)
        del outputLine

    print('Difference image created in %s' % output_file)


def mask_image(img, threshold, output_file):
    """Read an image and generates a mask with 1 where the pixel value is lower
    than the threshold and zero where it is greater.
    """
    image = gdal.Open(img, gdal.GA_ReadOnly)

    if image is None:
        print('The image could not be opened')
        sys.exit(-1)

    image_band = image.GetRasterBand(1)

    numLines = image_band.YSize

    driver = image.GetDriver()
    outDataset = driver.Create(output_file, image.RasterXSize,
        image.RasterYSize, 1, gdal.GDT_Float32)
    outDataset.SetGeoTransform(image.GetGeoTransform())
    outDataset.SetProjection(image.GetProjection())

    if outDataset is None:
        print('Could not create output image')
        sys.exit(-1)

    for line in range(numLines):
        outputLine = ''
        image_scanline = image_band.ReadRaster(0, line, image_band.XSize, 1,
            image_band.XSize, 1, gdal.GDT_Float32)
        image_tuple = struct.unpack('f' * image_band.XSize, image_scanline)

        for i in range(len(image_tuple)):
            if image_tuple[i] <= threshold:
                value = 1
            else:
                value = 0

            outputLine = outputLine + struct.pack('f', value)

        outDataset.GetRasterBand(1).WriteRaster(0, line, image_band.XSize, 1,
            outputLine, buf_xsize=image_band.XSize, buf_ysize=1,
            buf_type=gdal.GDT_Float32)
        del outputLine

    print('Mask image created in %s' % output_file)