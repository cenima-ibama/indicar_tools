indicar-tools
=============

Indicar Landsat Geoprocessing Tools

indicar-tools is the software made by the Indicar Project to process Landsat 8 imagery.

Commands:

RGB: creates only a RGB image, using the bands 6, 5 and 4. This RGB gives emphasys on the areas without vegetation.

    indicar.py process --rgb path

NDVI: creates only a NDVI image. Where there are clouds or cirrus, the pixel value will be 0.

    indicar.py process --ndvi path

Process: creates RGB, NDVI and a polygon containing the losses in the vegetation of the imagery in comparison with the NDVI of the same scene generated 16 days ago.

    indicar.py process path

path is the path for a compressed file containing the landsat imagery.
