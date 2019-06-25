"""insar.scripts.cli."""

import os

import click

import insar
from insar.enums import SARType
import logging


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
              default=SARType.uavsar, show_default=True)
@click.option('--threads', type=int, default=1)
@click.option('--config', type=click.Path(), default=None,
              help="TileDB config.")
@click.option('--tile_x_size', type=int, default=256)
@click.option('--tile_y_size', type=int, default=256)
@click.pass_context
def stack_sar(ctx, inputs, output, type_, threads, config,
              tile_x_size, tile_y_size):
    """Create TileDB SAR stack."""
    logger = logging.getLogger(__name__)
    try:
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

            insar.sar_translate(inputs, output, type_, threads, config,
                                tile_x_size, tile_y_size)
    except Exception:
        logger.exception("Exception caught during processing")
        raise click.Abort()
