""" Main routines for interferometric SAR processing with TileDB."""

import glob
import os

import rasterio

import xml.etree.ElementTree as ET


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


def stack(inputs, output, threads=1, config=None,
          tile_x_size=256, tile_y_size=256):
    """Ingests a temporal stack of uavsar SLC images.

    Returns
    -------
    tuple : (y, x) the padding in the row and column dimensions
    """
    parent_path = os.path.abspath(os.path.join(output, os.pardir))

    # find the first annotation file and read the dimensions
    prefix, segment_meta = read_ann(inputs[0])
    rows, cols = segment_meta['rows'], segment_meta['columns']

    # create a VRT file for processing the SLC files
    root = ET.Element('VRTDataset')
    root.set('rasterXSize', str(cols))
    root.set('rasterYSize', str(rows))

    data_path = os.path.abspath(os.path.join(inputs[0], os.pardir))
    lkv_file = glob.glob(os.path.join(data_path, '*.lkv'))[0]
    llh_file = glob.glob(os.path.join(data_path, '*.llh'))[0]
    lkv_factors = read_ll_meta(lkv_file, rows, cols)
    llh_factors = read_ll_meta(llh_file, rows, cols)

    # sort slc files by stack number
    data = {}
    for d in inputs:
        _, meta = read_ann(d)
        data[meta['stack_num']] = d

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
        source_filename.set('relativeToVRT', '1')
        source_filename.text = slc

        byte_order = ET.SubElement(band, 'ByteOrder')
        byte_order.text = 'LSB'

    stack_vrt = os.path.join(parent_path, 'stack.vrt')
    with open(stack_vrt, 'wb') as f:
        f.write(ET.tostring(root))

    # create sidecar VRT files for lkv and llh
    # first create intermediate tiff file, scale and reference with VRT
    for meta, factors in [(lkv_file, lkv_factors), (llh_file, llh_factors)]:
        root = ET.Element('VRTDataset')
        meta_cols = cols / factors[1]
        meta_rows = rows / factors[0]
        root.set('rasterXSize', str(meta_cols))
        root.set('rasterYSize', str(meta_rows))
        
        for i in range(3):
            b = ET.SubElement(root, 'VRTRasterBand')
            b.set('dataType', 'Float32')
            b.set('band', str(i + 1))
            b.set('subClass', 'VRTRawRasterBand')
            source_filename = ET.SubElement(b, 'SourceFilename')
            source_filename.set('relativeToVRT', '0')
            source_filename.text = meta
            image_offset = ET.SubElement(b, 'ImageOffset')
            image_offset.text = str(i * 4)
            pixel_offset = ET.SubElement(b, 'PixelOffset')
            pixel_offset.text = str(12)
            line_offset = ET.SubElement(b, 'LineOffset')
            line_offset.text = str(meta_cols * 3)

        output_vrt = meta + '.vrt'
        with open(os.path.join(data_path, output_vrt), 'wb') as f:
            f.write(ET.tostring(root))

    for t in ['lat', 'lon', 'height', 'north', 'east', 'up']:
        root = ET.Element('VRTDataset')
        root.set('rasterXSize', str(cols))
        root.set('rasterYSize', str(rows))

        band = ET.SubElement(root, 'VRTRasterBand')
        band.set('dataType', 'Float32')
        band.set('band', '1')
        simple_source = ET.SubElement(band, 'SimpleSource')
        simple_source.set('shared', '0')
        source_filename = ET.SubElement(simple_source, 'SourceFilename')
        source_filename.set('relativeToVRT', '1')
        source_filename.text = f"{t}.tif"
        source_band = ET.SubElement(simple_source, 'SourceBand')
        source_band.text = '1'

        with open(f"{t}.vrt", 'wb') as f:
            f.write(ET.tostring(root))

        with rasterio.open(stack_vrt) as src:
            profile = src.profile
            profile['driver'] = 'TileDB'
            profile['BLOCKXSIZE'] = tile_x_size
            profile['BLOCKYSIZE'] = tile_y_size
            if 'tiled' in profile:
                del profile['tiled']
            if config:
                profile['TILEDB_CONFIG'] = config

            with rasterio.open(output, 'w', **profile) as dst:
                windows = [window for _, window in dst.block_windows()]
                for window in windows:
                    data = src.read(window=window)
                    dst.write(data, window=window)


def num(s):
    try:
        return int(s)
    except ValueError:
        return float(s)
