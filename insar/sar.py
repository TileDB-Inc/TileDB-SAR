"""Generic algorithms for sar processing."""

import math
import random
import os
import string

import dask.array as da
from dask.distributed import Client
import numpy as np
import rasterio
from rasterio.dtypes import _gdal_typename
from rasterio.transform import Affine
import tiledb
import xarray as xr
import xml.etree.ElementTree as ET


client = None


def setup(n_workers=1, threads_per_worker=8):
    """ Setup Dask client."""
    global client
    client = Client(
                    n_workers=n_workers,
                    threads_per_worker=threads_per_worker)


def local_ccd(b1, b2):
    np.seterr(invalid='ignore')

    a12 = np.multiply(b1, np.conjugate(b1))
    a22 = np.multiply(b2, np.conjugate(b2))

    # element wise multiplication
    numer = 2 * np.sum(np.multiply(np.conjugate(b1), b2))

    # complex value but only the real elements are defined
    denom = np.sum(a12) + np.sum(a22)  # no noise assumed

    # maximum likelihood change approach
    alpha = abs(numer / denom)

    # constrain alpha to be in [0, 1]
    if alpha > 1 or math.isnan(alpha):
        alpha = 1.

    return alpha * np.ones(b1.shape, dtype=np.float)


def calculate_change(_input, bands, window, x, y, tile_x_size,
                     tile_y_size, output, config=None):
    # assuming average reflectivities in the entire two images are ~ equal
    # https://prod-ng.sandia.gov/techlib-noauth/access-control.cgi/2014/1418179.pdf
    # noise terms are known and are zero (uavsar, extend as we add additional sensors)
    cfg = tiledb.Config(config)
    ctx = tiledb.Ctx(config=cfg)
    with tiledb.DenseArray(output, 'w', ctx=ctx) as arr_output:
        with tiledb.DenseArray(_input, 'r', ctx=ctx) as arr:
            start_y = y * tile_y_size
            end_y = start_y + tile_y_size
            start_x = x * tile_x_size
            end_x = start_x + tile_x_size

            data = arr.query(attrs=['TDB_VALUES'])[:, start_y:end_y, start_x:end_x]  # noqa
            tile = data["TDB_VALUES"]
            out_tile = np.ones((tile.shape[1], tile.shape[2]), dtype=np.float32)  # noqa

            y1 = 0

            while y1 < tile_y_size:
                x1 = 0
                y1_end = y1 + window
                while x1 < tile_x_size:
                    x1_end = x1 + window
                    t1 = tile[0, y1:y1_end, x1:x1_end]
                    t2 = tile[1, y1:y1_end, x1:x1_end]

                    # write result to tiledb output array
                    out_tile[y1:y1_end, x1:x1_end] = local_ccd(t1, t2)  # noqa

                    x1 = x1 + window
                y1 = y1 + window

            # write out result tile 
            arr_output[start_y:end_y, start_x:end_x] = out_tile
    return True


def ccd(_input, bands, output=None, config=None, neighbourhood=7, overlap=1):
    if len(bands) == 2:
        if output is None or not os.path.exists(output):
            cfg = tiledb.Config(config)
            ctx = tiledb.Ctx(config=cfg)
            with tiledb.DenseArray(_input, 'r', ctx=ctx) as arr:
                y_dim = arr.schema.domain.dim(1)
                x_dim = arr.schema.domain.dim(2)
                height = y_dim.size
                width = x_dim.size
                tile_y_size = y_dim.tile
                tile_x_size = x_dim.tile

            dom = tiledb.Domain(
                    tiledb.Dim(domain=(0, height - 1),
                               tile=tile_y_size, dtype=np.uint64),
                    tiledb.Dim(domain=(0, width - 1),
                               tile=tile_x_size, dtype=np.uint64))

            schema = tiledb.ArraySchema(domain=dom, sparse=False,
                                        attrs=[tiledb.Attr(name="c",
                                               dtype=np.float32)], ctx=ctx)
            if output is None:
                output = _input + '_result_' + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(4))  # noqa

            tiledb.DenseArray.create(output, schema)

        x = da.from_tiledb(_input, storage_options=config)
        _, h, w = x.shape
        _, tile_y_size, tile_x_size = x.chunksize

        # w and h are an exact multiple of tile size
        n_tiles_x = w // tile_x_size
        n_tiles_y = h // tile_x_size

        # manually chunk and collect
        f = []

        for y in range(n_tiles_y):
            for x in range(n_tiles_x):
                f.append(client.submit(
                                    calculate_change,
                                    _input,
                                    bands,
                                    neighbourhood, x, y, tile_x_size,
                                    tile_y_size, output, config))
        client.gather(f)
        return output
    else:
        raise IndexError('CCD function requires two band indexes')


def stack(_input, output, tile_x_size, tile_y_size,
          config=None, attrs=None, bbox=None):
    with rasterio.open(_input) as src:
        profile = src.profile
        trans = Affine.to_gdal(src.transform)
        dt = np.dtype(src.dtypes[0])  # read first band data type

    # read initial image metadata
    profile['driver'] = 'TileDB'
    profile['blockxsize'] = tile_x_size
    profile['blockysize'] = tile_y_size
    if 'tiled' in profile:
        del profile['tiled']

    arr = xr.open_rasterio(_input,
                           chunks={'x': tile_x_size, 'y': tile_y_size})

    if bbox is None:
        w = profile['width']
        h = profile['height']
        bbox = (0, 0, w, h)
    else:
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]

    nBlocksX = math.ceil(w / (tile_x_size * 1.0))
    nBlocksY = math.ceil(h / (tile_y_size * 1.0))

    # GDAL TileDB driver writes/reads blocks so bypass rasterio
    dom = tiledb.Domain(
            tiledb.Dim(name='BANDS', domain=(0, profile['count'] - 1),
                       tile=1),
            tiledb.Dim(name='Y', domain=(0, (nBlocksY * tile_y_size) - 1),
                       tile=tile_y_size, dtype=np.uint64),
            tiledb.Dim(name='X', domain=(0, (nBlocksX * tile_x_size) - 1),
                       tile=tile_x_size, dtype=np.uint64))

    cfg = tiledb.Config(config)
    ctx = tiledb.Ctx(config=cfg)
    schema = tiledb.ArraySchema(domain=dom, sparse=False,
                                attrs=[tiledb.Attr(name="TDB_VALUES",
                                       dtype=dt)], ctx=ctx)

    tiledb.DenseArray.create(output, schema)
    with tiledb.DenseArray(output, 'w', ctx=ctx) as arr_output:
        arr[:, bbox[0]:bbox[2], bbox[1]:bbox[3]].data.to_tiledb(
            arr_output, storage_options=config)

    # write the GDAL metadata file from the source profile
    vfs = tiledb.VFS()
    meta = f"{output}/{os.path.basename(output)}.tdb.aux.xml"
    try:
        f = vfs.open(meta, "w")
        root = ET.Element('PAMDataset')
        geo = ET.SubElement(root, 'GeoTransform')
        geo.text = ', '.join(map(str, trans))
        meta = ET.SubElement(root, 'Metadata')
        meta.set('domain', 'IMAGE_STRUCTURE')
        t = ET.SubElement(meta, 'MDI')
        t.set('key', 'DATA_TYPE')
        t.text = _gdal_typename(np.complex128)
        nbits = ET.SubElement(meta, 'MDI')
        nbits.set('key', 'NBITS')
        nbits.text = str(dt.itemsize * 8)
        xsize = ET.SubElement(meta, 'MDI')
        xsize.set('key', 'X_SIZE')
        xsize.text = str(w)
        ysize = ET.SubElement(meta, 'MDI')
        ysize.set('key', 'Y_SIZE')
        ysize.text = str(h)
        vfs.write(f, ET.tostring(root))
    finally:
        vfs.close(f)
