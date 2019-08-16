""" Main routines for interferometric UAVSAR processing with TileDB."""

import glob
import logging
import math
import os

import insar.sar as sar

import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


def read_ann(file_name):
    """Reads the associated annotation file to a SLC image.

    Parameters
    ----------
    filename : string
        Path to a SLC image.
    Returns
    -------
    string, dict : Identifier for the image segment and down-sample and a
    dictionary of the available metadata.
    """
    parts = file_name[:-4].split('_')
    t = f"slc_{parts[-2][1:]}_{parts[-1:][0]}"  # segment and down-sample ext
    ann_fname = '_'.join(parts[:-2]) + '.ann'
    segment_meta = {}

    with open(ann_fname) as meta:
        for line in meta.readlines():
            if line.startswith(t):
                vals = line[len(t) + 1:].split()
                try:
                    segment_meta[vals[0].lower()] = num(vals[3])
                except ValueError:
                    segment_meta[vals[0].lower()] = vals[3]
            elif line.startswith('Stack Line Number'):
                segment_meta['stack_num'] = int(line.split()[5])

    return t, segment_meta


def read_ll_meta(file_name, rows, columns):
    """Reads the SLC llh/lkv sidecar file

    Parameters
    ----------
    filename : string
        Path to a llh/lkv image.
    rows : int
        Number of rows in the image.
    cols : int
        Number of columns in the image.
    Returns
    -------
    tuple : downsample factors (rows/cols)
    """
    # filename contains down sampling factor e.g. site_line_stack_BC_s1_2x8.llh
    down_sample = file_name.split('_')[-1][:-4].split('x')
    factors = tuple(map(lambda x: int(x), down_sample))

    return factors


def stack(inputs, output, config=None,
          tile_x_size=1024, tile_y_size=1024, bbox=None):
    """Ingests a temporal stack of uavsar SLC images."""
    # find the first annotation file and read the dimensions
    prefix, segment_meta = read_ann(inputs[0])
    if 'rows' in segment_meta:
        rows, cols = segment_meta['rows'], segment_meta['columns']
    else:
        rows, cols = segment_meta['slc_mag.set_rows'], segment_meta['slc_mag.set_cols']  # noqa

    # create a VRT file for processing the SLC files
    root = ET.Element('VRTDataset')
    root.set('rasterXSize', str(cols))
    root.set('rasterYSize', str(rows))

    data_path = os.path.dirname(os.path.abspath(inputs[0]))

    if len(glob.glob(os.path.join(data_path, '*.lkv'))) > 0:
        lkv_file = glob.glob(os.path.join(data_path, '*.lkv'))[0]
        llh_file = glob.glob(os.path.join(data_path, '*.llh'))[0]
        lkv_factors = read_ll_meta(lkv_file, rows, cols)
        llh_factors = read_ll_meta(llh_file, rows, cols)
    else:
        lkv_file = None
        llh_file = None
        lkv_factors = None
        llh_factors = None

    # sort slc files by stack number
    data = {}
    for k, d in enumerate(inputs):
        _, meta = read_ann(d)
        if 'stack_num' in meta:
            data[meta['stack_num']] = d
        else:
            data[k] = d

    for idx in sorted(data):
        slc = data[idx]

        band = ET.SubElement(root, 'VRTRasterBand')
        band.set('dataType', 'CFloat64')
        band.set('band', str(idx))
        band.set('subClass', 'VRTRawRasterBand')
        metadata = ET.SubElement(band, 'Metadata')
        mdi = ET.SubElement(metadata, 'MDI')
        mdi.set('key', 'source')
        mdi.text = os.path.splitext(slc)[0][2:]
        source_filename = ET.SubElement(band, 'SourceFilename')
        source_filename.set('relativeToVRT', '0')
        source_filename.text = slc

        byte_order = ET.SubElement(band, 'ByteOrder')
        byte_order.text = 'LSB'

    stack_vrt = os.path.join(data_path, 'stack.vrt')

    with open(stack_vrt, 'wb') as f:
        f.write(ET.tostring(root))

    # create sidecar VRT files for lkv and llh
    attrs = {}
    if lkv_file is not None:
        for meta, factors, bands in [
            (lkv_file, lkv_factors, ('east', 'north', 'up')),
            (llh_file, llh_factors, ('lat', 'lon', 'height'))
        ]:
            root = ET.Element('VRTDataset')
            meta_cols = math.ceil(cols / factors[1])
            meta_rows = math.ceil(rows / factors[0])
            root.set('rasterXSize', str(meta_cols))
            root.set('rasterYSize', str(meta_rows))

            i = 1
            for b in bands:
                band = ET.SubElement(root, 'VRTRasterBand')
                band.set('dataType', 'Float32')
                band.set('band', str(1))
                band.set('subClass', 'VRTRawRasterBand')
                source_filename = ET.SubElement(band, 'SourceFilename')
                source_filename.set('relativeToVRT', '0')
                source_filename.text = meta
                image_offset = ET.SubElement(band, 'ImageOffset')
                image_offset.text = str((i - 1) * 4)
                pixel_offset = ET.SubElement(band, 'PixelOffset')
                pixel_offset.text = str(12)
                line_offset = ET.SubElement(band, 'LineOffset')
                line_offset.text = str(meta_cols * 3)
                i = i + 1

                output_vrt = os.path.join(data_path, b + '.vrt')
                with open(output_vrt, 'wb') as f:
                    f.write(ET.tostring(root))
                    attrs[b] = output_vrt

    sar.stack(stack_vrt, output, tile_x_size, tile_y_size,
              config, attrs=attrs, bbox=bbox)


def num(s):
    try:
        return int(s)
    except ValueError:
        return float(s)
