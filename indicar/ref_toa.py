# -*-coding:Latin-1 -*
"""
/***************************************************************************
 A Geosud tool to convert Spot DN to Top of Atmosphere (TOA) Reflectance
                              -------------------
        begin                : 2014-02-26
        copyright            : (C) 2014 by Kenji Ose / UMR Tetis - Irstea
        email                : kenji.ose@teledetection.fr
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from __future__ import print_function
import sys
import numpy
import os
import time
import glob
from osgeo import gdal
from osgeo.gdalconst import *


# Class Landsat 8 (LDCM)
class Landsat8:

    def __init__(self, metafile):
        """
        Metadata for conversion to TOA Radiance and TOA Reflectance
        """
        print('metadata filename: %s' % (metafile))
        startTime = time.time()
        meta = open(metafile, 'r')
        metalines = meta.readlines()
        self.root = {}
        for line in metalines:
            if any(i in line for i in ('REFLECTANCE_MULT_BAND_',
                                        'REFLECTANCE_ADD_BAND_',
                                        'K1_CONSTANT_BAND_', 'K2_CONSTANT_BAND_',
                                        'SUN_AZIMUTH', 'SUN_ELEVATION')):
                self.root[line.split('=')[0].strip()] = float(line.split('=')[1].strip())
        metalines = None
        meta.close()
        endTime = time.time()
        print('parsing duration: %s seconds' % (endTime - startTime))

    def getGain(self):
        """
        List of Landsat band-specific multiplicative rescaling factor and
        Band-specific additive rescaling factor
        (coastal/aerosol, blue, green, red, nir, swir1, swir2, pan, cirrus)
        """
        self.gain = [self.root['REFLECTANCE_MULT_BAND_%s' %(i+1)] for i in range(9)]
        self.add = [self.root['REFLECTANCE_ADD_BAND_%s' %(i+1)] for i in range(9)]

    def getSolarAngle(self):
        """
        Solar Zenithal and Azimuthal Angles in degrees
        """
        self.solarZAngle = 90 - self.root['SUN_ELEVATION']
        self.solarAAngle = self.root['SUN_AZIMUTH']

    def getBandList(self, dirname):
        self.bandList = glob.glob(os.path.join(dirname, 'LC*B[1-9].TIF'))

    def getDistEarthSun(self):
        self.distEarthSun = 'not required'

    def getSolarIrrad(self):
        self.eSun = ['not required']

    def reflectanceToa(self, bandList, outname='refToa.tif', bitcode='32', outpath=None):
        """
        TOA Reflectance
        Equation for Landsat 8:
        r = (M*CN+A)/cos(thZ)
        with r for TOA reflectance
             M for band-specific multiplicative rescaling factor
             CN for pixel value (digital number)
             A for Band-specific additive rescaling factor
             thZ for Solar Zenithal angle
        """
        startTime = time.time()
        # image driver
        driver = gdal.GetDriverByName('GTiff')
        driver.Register()
        # image opening
        idBand = {int(os.path.splitext(os.path.basename(i))[0][-1])-1:i for i in bandList}
        for band in idBand.keys():
            print(band)
            imgfile = idBand[band]
            print(imgfile)
            inDs = gdal.Open(imgfile, GA_ReadOnly)
            if inDs is None:
                print('could not open %s' % imgfile)
                sys.exit(1)
            # image size and tiles
            cols = inDs.RasterXSize
            rows = inDs.RasterYSize
            bands = inDs.RasterCount
            xBSize = 60
            yBSize = 60
            # output image name
            if bitcode == '32':
                codage = GDT_Float32
                nptype = numpy.float
                maxi = 1
            elif bitcode == '16':
                codage = GDT_UInt16
                nptype = numpy.uint16
                maxi = 1000

            if outpath:
                outDs = driver.Create('%s%s' % (os.path.join(outpath, os.path.splitext(os.path.basename(imgfile))[0]), outname),
                                      cols, rows, bands, codage)
            else:
                outDs = driver.Create('%s%s' % (os.path.splitext(imgfile)[0], outname),
                                      cols, rows, bands, codage)
            if outDs is None:
                print('could not create %s%s' % (os.path.splitext(imgfile)[0], outname))
                sys.exit(1)

            outBand = outDs.GetRasterBand(1)
            canal = inDs.GetRasterBand(1)
            # line search
            for i in range(0, rows, yBSize):
                if i + yBSize < rows:
                    numRows = yBSize
                else:
                    numRows = rows - i
                # column search
                for j in range(0, cols, xBSize):
                    if j + xBSize < cols:
                        numCols = xBSize
                    else:
                        numCols = cols - j
                    data = canal.ReadAsArray(j, i, numCols, numRows).astype(numpy.float)
                    # TOA Reflectance with correction for sun angle
                    toa = (maxi * (self.gain[band] * data + self.add[band]) /
                           (numpy.cos(numpy.radians(self.solarZAngle)))
                           ).astype(nptype)
                    # saturated pixels (> 1 or > 1000)
                    mask = numpy.less_equal(toa, maxi)
                    toa = numpy.choose(mask, (maxi, toa))
                    outBand.WriteArray(toa, j, i)
            outBand.FlushCache()
            stats = outBand.GetStatistics(0, 1)
            outBand = None
            canal = None
            # projection import
            outDs.SetGeoTransform(inDs.GetGeoTransform())
            outDs.SetProjection(inDs.GetProjection())
            # pyramid layers processing
            gdal.SetConfigOption('USE_RRD', 'YES')
            outDs.BuildOverviews(overviewlist=[2, 4, 8, 16, 32, 64, 128])
            inDs = None
            outDs = None
        endTime = time.time()
        print('reflectance processing duration: %s seconds' % str(endTime - startTime))