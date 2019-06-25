"""insar: Interferometric SAR processing using TileDB."""


from insar.enums import SARType
import logging
from insar.uavsar import *


__version__ = "1.0.0"


def sar_translate(inputs, output, type_, threads, config, tile_x_size,
                  tile_y_size):
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
    """
    logger = logging.getLogger(__name__)
    if SARType[type_] == SARType.uavsar:
        uavsar.stack(inputs, output, threads, config, tile_x_size, tile_y_size)
    else:
        logger.exception('Unable to process selected SAR sensor type.')
