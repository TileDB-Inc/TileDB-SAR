"""insar: Interferometric SAR processing using TileDB."""

import dask.array as da
import dask_image.ndfilters

from insar.enums import SARType, SARDespeckleType, SARFunctionType
import logging
from insar.uavsar import *
from insar.sar import *


__version__ = "1.0.0"


logger = logging.getLogger(__name__)


def process(_input, function, bands=(0, 1), config=None, window=5, output=None):
    """Reads the associated annotation file to a SLC image.

    Parameters
    ----------
    input : string
        Path to a TileDB stack.
    function: enum
        InSAR function type to apply.
    window:: int
        Rolling window size
    output: array
        TileDB output array

    Returns
    ------
    list : list of tiles and jobs completed
    """        
    if SARFunctionType[function] == SARFunctionType.ccd:
        return ccd(_input, bands, output, config)
    else:
        logger.exception(f"Unable to select depeckle type {filter}.")


def despeckle(input, filter, config=None, window=5):
    """Despeckles an SLC stack.

    Parameters
    ----------
    input : string
        Path to a TileDB stack.
    filter: enum
        Filter type to apply.
    window:: int
        Rolling window size

    Returns
    ------
    array: filtered array type
    """
    # reference - https://examples.dask.org/applications/image-processing.html
    if SARDespeckleType[filter] == SARDespeckleType.median:
        arr = da.from_tiledb(input, storage_options=config)
        return dask_image.ndfilters.median_filter(arr, window)
    else:
        logger.exception(f"Unable to select depeckle type {filter}.")


def sar_translate(inputs, output, type_, config, tile_x_size,
                  tile_y_size, bbox=None):
    """Translates the input files to an output TileDB array

    Parameters
    ----------
    inputs : list
        Paths to a SLC images.
    output : string
        Path to output TileDB stack.
    type_ : enum
        SAR Sensor type.
    tile_x_size : int
        Size of tile in x direction.
    tile_y_size : int
        Size of tile in y direction.
    threads : int
        Number of threads to use in the format translation.
    output : string
        Path to output TileDB stack.
    config : path
        If set the path to a TileDB configuration file.
    tile_x_size : int
            Tile dimension in x direction.
    tile_y_size : int
            Tile dimension in y direction.
    bbox : list
            Subset dimensions of input.
    """
    if SARType[type_] == SARType.uavsar:
        uavsar.stack(inputs, output, config, tile_x_size, tile_y_size, bbox)
    else:
        logger.exception('Unable to process selected SAR sensor type.')
