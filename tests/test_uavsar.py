"""Tests the UAVSAR parser."""

import glob
import os

import pytest

from insar import uavsar


@pytest.fixture(scope='session')
def data_dir():
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')


@pytest.fixture(scope='session', autouse=True)
def clean_vrt(data_dir):
    vrts = glob.glob(os.path.join(data_dir, '*.vrt'))
    for vrt in vrts:
        os.remove(vrt)


def test_read_ann(data_dir):
    meta_files = glob.glob(os.path.join(data_dir, '*.slc'))
    prefix, meta = uavsar.read_ann(meta_files[0])
    assert prefix == 'slc_1_1x1'

    with pytest.raises(FileNotFoundError):
        uavsar.read_ann(
            '/foo/Test_XXXXX_XXXXX_002_XXXXXX_XXXHH_02_BC_s1_1x1.slc')

    with pytest.raises(IndexError):
        uavsar.read_ann('/foo/Test.slc')

    assert meta['rows'] == 20
    assert meta['columns'] == 10
    assert meta['stack_num'] == 2


def test_read_llh(data_dir):
    llh_file = os.path.join(data_dir, 'Test_XXXXX_02_BC_s1_2x2.llh')
    factor = uavsar.read_ll_meta(llh_file, 20, 10)
    assert factor == (2, 2)


def test_read_lkv(data_dir):
    lkv_file = os.path.join(data_dir, 'Test_XXXXX_02_BC_s1_2x2.lkv')
    factor = uavsar.read_ll_meta(lkv_file, 20, 10)
    assert factor == (2, 2)


def test_stack(data_dir, tmpdir):
    output = os.path.join(tmpdir, 'test_array')
    inputs = glob.glob(os.path.join(data_dir, '*.slc'))
    uavsar.stack(inputs, output, tile_x_size=3, tile_y_size=7)
    assert os.path.exists(output)
