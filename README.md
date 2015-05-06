indicar-tools
=============

Indicar Landsat Geoprocessing Tools

indicar-tools is the software made by the Indicar Project to process Landsat 8 imagery.

#### Installation

    pip install git+https://github.com/ibamacsr/indicar-tools/#egg=indicar-tools

#### Commands:

**Process**: Process: creates RGB, NDVI and a raster change detection file containing the losses in the vegetation of the imagery in comparison with the NDVI of the same scene generated 16 days ago.

    indicar process path

If you want the change detection as a vector file instead of a raster, use the --polygonize parameter:

    indicar process path --polygonize

`path` is the path to the compressed LC8 file or to a folder containing the uncompressed files.

**RGB**: creates only a RGB image, using the bands 6, 5 and 4. This composition gives emphasys to the areas without vegetation.

    indicar process --rgb path

**NDVI**: creates only a NDVI image. Where there are clouds or cirrus, the pixel value will be 0.

    indicar process --ndvi path

**Set Directory**: by default, indicar-tools will save the processed images in a folder named 'landsat' on your home dir, but you can set an alternative directory using the `--dir` parameter.

    indicar process path --dir directory_path

#### Requirements

GDAL >= 1.9


#### License

GPL 3
