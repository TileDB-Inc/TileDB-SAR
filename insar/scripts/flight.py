"""insar.scripts.flight."""

import logging
import os

import click

import struct

import insar


@click.group(short_help="Flight metadata related utilities.")
@click.pass_context
def flight():
    """Rasterio insar subcommands."""
    pass


@flight.command(short_help="Create flight path.")
@click.argument('input_', type=click.Path())
@click.argument('interval', type=int, default=100)
@click.option('--type', '-t', 'type_', help="SAR sensor type.",
              type=click.Choice(
                  [it.name for it in insar.SARType if it.value in [0]]),
              default=insar.SARType.uavsar, show_default=True)
@click.pass_context
def flight_path(ctx, input_, interval, type_):
    """Create GeoJSON flight path."""
    logger = logging.getLogger(__name__)
    if not os.path.exists(input_):
        logger.exception(f"{input_} does not exist.")
        raise click.Abort()

    lat, lon = -90.0, -180.0

    with open(input_, 'rb') as f:
        cntr = 0
        while True:
            data = f.read(12)
            if not data and cntr % interval != 0:
                print(create_waypoint(lon, lat, cntr))
                break

            if cntr == 0 or cntr % interval == 0:
                lat, lon, _ = struct.unpack('fff', data)
                print(create_waypoint(lon, lat, cntr))
            cntr = cntr + 1


def create_waypoint(lon, lat, id):
    return "{\"type\":\"Feature\",\"geometry\":" \
           f"{{\"type\":\"Point\",\"coordinates\":[{lon},{lat}]}}," \
           f"\"properties\":{{\"id\":{id}}}}}"
