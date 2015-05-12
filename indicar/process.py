# Indicar Landsat Geoprocessing Tools
#
#
# Author: Hex Gis
# Contributor: willemarcel
#
# License: GPLv3

from __future__ import print_function
from datetime import date, timedelta
from subprocess import call
from shutil import rmtree
import struct
import os

from osgeo import gdal

from .gdal_operations import *
from .ref_toa import Landsat8


def check_create_folder(folder_path):
    """Check whether a folder exists, if not the folder is created.
    Always return folder_path.
    """
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print("%s folder created" % folder_path)

    return folder_path


def three_digit(number):
    """ Add 0s to inputs that their length is less than 3.
    For example: 1 --> 001 | 02 --> 020 | st --> 0st
    """
    number = str(number)
    if len(number) == 1:
        return '00%s' % number
    elif len(number) == 2:
        return '0%s' % number
    else:
        return number


def get_file(path):
    """Separate the name of the file or folder from the path and return it
    Example: /path/to/file ---> file
    """
    return os.path.basename(path)


def get_last_image_name(image):
    """Returns the name of the 16 days ago landsat image"""
    year, day = (image[9:13], image[13:16])

    last_date = (date(int(year), 1, 1) + timedelta(int(day) - 17))
    last_year = last_date.year
    last_day = (last_date - date(last_year, 1, 1)).days + 1

    return "%s%s%s%s" % (image[:9], last_year, three_digit(last_day), image[16:])


def get_image_bounds(image_path):
    """Return the coordinates of the lower left (minx, miny) and the
    upper right (maxx, maxy) of the image.
    """
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
    """Return the intersection bounds of 2 images. The method used is to get
    the max value of the minx and miny and the minimum value of maxx and maxy.
    """
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

    def __init__(self, path, base_dir=None):
        """Initating the Process class

        Arguments:
        path - string containing the path of the landsat 8 folder or compressed file

        """
        path = path.rstrip('/')
        self.image = get_file(path).split('.')[0]

        if path.endswith('.tar.gz'):
            if not base_dir:
                base_dir = os.path.join(os.path.expanduser('~'), 'landsat')
            self.src_image_path = os.path.join(base_dir, self.image)
            check_create_folder(self.src_image_path)
            self.extract(path, self.src_image_path)
        else:
            if os.path.isdir(path):
                self.src_image_path = path
            else:
                self.src_image_path = os.path.join(os.path.expanduser('~'), 'landsat', path)

        self.b4 = os.path.join(self.src_image_path, self.image + '_B4.TIF')
        self.b5 = os.path.join(self.src_image_path, self.image + '_B5.TIF')
        self.b6 = os.path.join(self.src_image_path, self.image + '_B6.TIF')
        self.bqa = os.path.join(self.src_image_path, self.image + '_BQA.TIF')
        self.mtl = os.path.join(self.src_image_path, self.image + '_MTL.txt')
        self.ndvi = os.path.join(self.src_image_path, self.image + '_ndvi.tif')

    def full(self, polygonize=False):
        """Make RGB, NDVI and change_detection"""
        self.make_rgb()
        self.make_ndvi()
        self.change_detection(polygonize)

    def extract(self, src, dst):
        """Extract the Landsat 8 file."""
        print("Extracting %s - It might take some time" % self.image)
        call(['tar', '-xzf', src, '-C', dst])

    def make_rgb(self):
        """Make a RGB Image using the bands 6, 5 and 4."""
        vrt = os.path.join(self.src_image_path, self.image + '.vrt')
        rgb = os.path.join(self.src_image_path, self.image + '_r6g5b4.tif')
        call(['gdalbuildvrt', '-q', '-separate', vrt, self.b6, self.b5, self.b4])
        call(['gdal_translate', '-q', '-co', 'COMPRESS=LZW', vrt, rgb])

        os.remove(vrt)

        try:
            check_integrity(rgb)
            print('Created RGB file in %s' % rgb)
            return rgb
        except RasterFileIntegrityError:
            print('Error on RGB file creation')
            return False

    def make_ndvi(self):
        """Generate a NDVI image using the Top of Atmosphere Reflectance images.
        If the BQA value indicates cloud or cirrus or if the pixel value in B6
        is lower than 0.1, the NDVI value will be zero.
        """
        self.make_ref_toa()

        b4 = gdal.Open(self.b4_toa, gdal.GA_ReadOnly)
        b5 = gdal.Open(self.b5_toa, gdal.GA_ReadOnly)
        b6 = gdal.Open(self.b6_toa, gdal.GA_ReadOnly)
        bqa = gdal.Open(self.bqa, gdal.GA_ReadOnly)

        if b4 is None or b5 is None or b6 is None or bqa is None:
            print("Some of the datasets could not be opened")
        else:
            red_band = b4.GetRasterBand(1)
            nir_band = b5.GetRasterBand(1)
            b6_band = b6.GetRasterBand(1)
            bqa_band = bqa.GetRasterBand(1)
            numLines = red_band.YSize

            bqa_values = [61440, 59424, 57344, 56320, 53248, 52256, 52224,
                49184, 49152, 48128, 45056, 43040, 39936, 36896, 36864, 32768,
                31744, 28672]

            driver = b4.GetDriver()
            outDataset = driver.Create(self.ndvi, b4.RasterXSize, b4.RasterYSize,
                1, gdal.GDT_Float32)
            outDataset.SetGeoTransform(b4.GetGeoTransform())
            outDataset.SetProjection(b4.GetProjection())

            for line in range(numLines):
                outputLine = ''
                red_scanline = red_band.ReadRaster(0, line, red_band.XSize, 1,
                    red_band.XSize, 1, gdal.GDT_Float32)
                red_tuple = struct.unpack('f' * red_band.XSize, red_scanline)

                nir_scanline = nir_band.ReadRaster(0, line, nir_band.XSize, 1,
                    nir_band.XSize, 1, gdal.GDT_Float32)
                nir_tuple = struct.unpack('f' * nir_band.XSize, nir_scanline)

                b6_scanline = b6_band.ReadRaster(0, line, b6_band.XSize, 1,
                    b6_band.XSize, 1, gdal.GDT_Float32)
                b6_tuple = struct.unpack('f' * b6_band.XSize, b6_scanline)

                bqa_scanline = bqa_band.ReadRaster(0, line, bqa_band.XSize, 1,
                    bqa_band.XSize, 1, gdal.GDT_Float32)
                bqa_tuple = struct.unpack('f' * bqa_band.XSize, bqa_scanline)

                for i in range(len(red_tuple)):
                    if bqa_tuple[i] in bqa_values:
                        ndvi = 0
                    elif b6_tuple[i] < 0.1:
                        ndvi = 0
                    else:
                        ndvi_lower = (nir_tuple[i] + red_tuple[i])
                        ndvi_upper = (nir_tuple[i] - red_tuple[i])
                        ndvi = 0
                        if ndvi_lower == 0:
                            ndvi = 0
                        else:
                            ndvi = ndvi_upper / ndvi_lower

                    outputLine = outputLine + struct.pack('f', ndvi).decode('utf-8')

                outDataset.GetRasterBand(1).WriteRaster(0, line, red_band.XSize,
                    1, outputLine, buf_xsize=red_band.XSize, buf_ysize=1,
                    buf_type=gdal.GDT_Float32)
                del outputLine

            #remove toa files
            for toa in [self.b4_toa, self.b5_toa, self.b6_toa]:
                os.remove(toa)
                os.remove(toa.replace('.tif', '.aux'))

            if os.path.isfile(self.ndvi):
                try:
                    check_integrity(self.ndvi)
                    print('NDVI Created in %s' % self.ndvi)
                    return self.ndvi
                except RasterFileIntegrityError:
                    print('NDVI could not be created')
                    return False
            else:
                print('NDVI could not be created')
                return False

    def change_detection(self, polygonize=False):
        """The process of change detection involves the following steps:
            1. Warp NDVI images if it has differents coordinates and resolutions
            2. Subtract NDVI images
            3. Mask the image generated by the subtract, putting the value 1
                where the pixel value is less than -0.08 and putting the value
                0 in the others pixels
            4. Sieve the image, removing areas lower than 33 pixels
            5. If polygonize is true:
                5.1 Polygonize the sieve image creating a Shapefile
                5.2 Convert the Shapefile to GeoJSON reprojecting it to Sirgas 2000
        """

        last_image = get_last_image_name(self.image)
        last_ndvi = os.path.join(self.src_image_path.replace(self.image, ''),
            last_image, last_image + '_ndvi.tif')

        if os.path.isfile(self.ndvi) and os.path.isfile(last_ndvi):
            ndvi_warp = os.path.join(self.src_image_path,
                self.image + '_ndvi_warp.tif')
            last_ndvi_warp = os.path.join(self.src_image_path.replace(self.image, ''),
                last_image, last_image + '_ndvi_warp.tif')
            changes = os.path.join(self.src_image_path,
                self.image + '_changes.tif')
            changes_mask = os.path.join(self.src_image_path,
                self.image + '_changes_mask.tif')
            sieve = os.path.join(self.src_image_path,
                self.image + '_detection.tif')

            # verify if the images has different coordinates, if yes, warp them
            if get_image_bounds(self.ndvi) != get_image_bounds(last_ndvi):
                bounds = get_intersection_bounds(self.ndvi, last_ndvi)
                warp_image(self.ndvi, bounds, ndvi_warp)
                warp_image(last_ndvi, bounds, last_ndvi_warp)
                subtract(ndvi_warp, last_ndvi_warp, changes)
            else:
                subtract(self.ndvi, last_ndvi, changes)

            mask_image(changes, -0.08, changes_mask)
            # remove areas lower than 33 pixels what represents 30000 sq metres
            call(['gdal_sieve.py', '-st', '33', changes_mask, sieve])
            result_file = sieve

            if polygonize is True:
                # create a folder to shp files because it's more than one file
                detection_shp = os.path.join(
                    check_create_folder(os.path.join(self.src_image_path, 'shp')),
                    self.image + '_detection.shp')
                detection_geojson = os.path.join(self.src_image_path,
                    self.image + '_detection.geojson')

                # polygonize sieve file to shapefile
                call(['gdal_polygonize.py', sieve, '-f', 'ESRI Shapefile',
                    detection_shp])
                # convert to GeoJSON, reproject in Sirgas 2000 and filter areas
                # with DN=1 to get only the areas where the pixel had
                # value 1 in the changes_mask
                call(['ogr2ogr', '-where', '"DN"=1', '-t_srs', 'EPSG:4674',
                    '-f', 'GeoJSON', detection_geojson, detection_shp])
                os.remove(sieve)
                result_file = detection_geojson

                # remove shp folder
                rmtree(os.path.join(self.src_image_path, 'shp'))

            # remove intermediate files
            file_list = [ndvi_warp, last_ndvi_warp, changes, changes_mask]
            for f in file_list:
                if os.path.isfile(f):
                    os.remove(f)

            print('Change detection created in %s' % result_file)
            return result_file
        else:
            print('Change detection was not executed because some NDVI image is missing.')
            return False


    def make_ref_toa(self):
        """Convert the bands 4, 5 and 6 from Spot DN to Top of Atmosphere (TOA)
        Reflectance."""

        self.b4_toa = os.path.join(self.src_image_path, self.image + '_B4_toa.tif')
        self.b5_toa = os.path.join(self.src_image_path, self.image + '_B5_toa.tif')
        self.b6_toa = os.path.join(self.src_image_path, self.image + '_B6_toa.tif')

        if os.path.isfile(self.mtl):
            image = Landsat8(self.mtl)
            image.getGain()
            image.getSolarAngle()
            image.getSolarIrrad()
            image.reflectanceToa([self.b4, self.b5, self.b6],
                outname='_toa.tif',
                outpath=self.src_image_path)
        else:
            print("""Could not make TOA Reflectance images because MTL file
                was not found""")
