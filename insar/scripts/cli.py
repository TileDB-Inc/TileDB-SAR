"""insar.scripts.cli."""

import configparser
import logging
import os


import click
import tiledb

import insar


def tiledb_config_handler(ctx, param, value):
    """Process and validate input file names"""
    if value is not None:
        cfg = '[root]\n' + value.read()
        parser = configparser.RawConfigParser()
        parser.read_string(cfg)
        root = parser['root']
        temp_dict = {}
        for key in root.iterkeys():
            temp_dict[key] = root[key]
        return temp_dict
    else:
        return {}


@click.group(short_help="Translate SAR stacks to TileDB arrays.")
@click.pass_context
def sar():
    """Rasterio insar subcommands."""
    pass


@sar.command(short_help="Create InSAR stack.")
@click.argument('inputs', nargs=-1, type=click.Path())
@click.option('--output', help="Output array.")
@click.option('--type', '-t', 'type_', help="SAR sensor type.",
              type=click.Choice(
                  [it.name for it in insar.SARType if it.value in [0]]),
              default=insar.SARType.uavsar, show_default=True)
@click.option('--function', '-f', 'function', help="InSAR function type.",
              type=click.Choice(
                  [it.name for it in insar.SARFunctionType
                   if it.value in [0]]),
              default=None, show_default=True)
@click.option('--bands', nargs=2, type=int, default=(0, 1), help="InSAR bands")
@click.option('--window_size', type=int, default=5)
@click.option('--config', type=click.File('r'), default=None,
              callback=tiledb_config_handler, help="TileDB config.")
@click.option('--tile_x_size', type=int, default=1024)
@click.option('--tile_y_size', type=int, default=1024)
@click.option('--bbox', nargs=4, type=int, help="subset box, minx,miny,maxx,maxy")
@click.option('--n_workers', type=int, default=1, help="number of dask workers")
@click.option('--threads_per_worker', type=int, default=4, help="dask threads per worker")
@click.pass_context
def stack_sar(ctx, inputs, output, type_, function, bands,
              window_size, config, tile_x_size, tile_y_size, bbox,
              n_workers, threads_per_worker):
    """Create TileDB SAR stack."""
    logger = logging.getLogger(__name__)
    try:
        insar.sar.setup(n_workers, threads_per_worker)
        with ctx.obj['env']:
            if output is None:
                inputs = inputs[:-1]
                output = inputs[-1]

            for f in inputs:
                if not os.path.exists(f):
                    logger.exception(f"{f} does not exist.")
                    raise click.Abort()

            if os.path.exists(output):
                logger.exception(f"{output} already exists.")
                raise click.Abort()

            if (len(bbox) > 0):
                insar.sar_translate(inputs, output, type_, config,
                                    tile_x_size, tile_y_size, bbox)
            else:
                insar.sar_translate(inputs, output, type_, config,
                                    tile_x_size, tile_y_size)

            if function is not None:
                insar.process(
                              output, function,
                              bands, config=config
                             )

    except Exception:
        logger.exception("Exception caught during processing")
        raise click.Abort()


@sar.command(short_help="Create InSAR stack.")
@click.argument('input_', type=click.Path())
@click.option('--output', help="Output array.")
@click.option('--function', '-f', 'function', help="InSAR function type.",
              type=click.Choice(
                  [it.name for it in insar.SARFunctionType
                   if it.value in [0]]),
              default=None, show_default=True)
@click.option('--bands', nargs=2, type=int, default=(0, 1), help="InSAR bands")
@click.option('--config', type=click.File('r'), default=None,
              callback=tiledb_config_handler, help="TileDB config.")
@click.option('--n_workers', type=int, default=1, help="number of dask workers")
@click.option('--threads_per_worker', type=int, default=4, help="dask threads per worker")
@click.pass_context
def process_stack(ctx, input_, output, function, bands, config, n_workers, threads_per_worker):
    """Process TileDB SAR stack."""
    logger = logging.getLogger(__name__)
    try:
        insar.sar.setup(n_workers, threads_per_worker)
        with ctx.obj['env']:
            if not os.path.exists(input_):
                logger.exception(f"{input_} does not exist.")
                raise click.Abort()

            if os.path.exists(output):
                logger.exception(f"{output} already exists.")
                raise click.Abort()

            insar.process(
                          input_, function,
                          bands, output=output, config=config
                         )
    except Exception:
        logger.exception("Exception caught during processing")
        raise click.Abort()


def save(arr, output, config):
    with tiledb.DenseArray(output, 'w') as dst:
        arr.to_tiledb(dst, storage_options=config)

