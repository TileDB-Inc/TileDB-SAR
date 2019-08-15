"""Tests the UAVSAR parser."""

import glob
import math
import os

import dask.array as da
import numpy as np
import pytest

from insar import uavsar
from insar.sar import local_ccd

mu, sigma = 0.5, 0.24
window = 7


@pytest.fixture(scope='session')
def data_dir():
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')


@pytest.fixture(scope='session', autouse=True)
def clean_vrt(data_dir):
    vrts = glob.glob(os.path.join(data_dir, '*.vrt'))
    for vrt in vrts:
        os.remove(vrt)


def add_change(x):
    # use zero for thermal noise in this synthetic dataset
    r = np.random.rand()
    # weight shift to determine alpha
    return x * r + math.sqrt(1 - r**2) * x


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


def test_no_ccd():
    window = 7
    s = np.random.normal(mu, sigma, 10000)
    data = s.reshape((100, 100))
    arr1 = data + 1.j*data
    arr2 = np.copy(arr1)
    da1 = da.from_array(arr1).rechunk((window, window))
    da2 = da.from_array(arr2).rechunk((window, window))
    result = da.map_blocks(local_ccd, da1, da2).compute()

    # expect the result to indicate no change
    np.testing.assert_allclose(
            result.real, np.ones(10000, dtype=np.float).reshape((100, 100)))


def test_ccd():
    np.random.seed(0)
    s = np.random.normal(mu, sigma, 10000)
    data = s.reshape((100, 100))
    arr1 = data + 1.j*data
    
    arr2 = np.copy(arr1)
    # treat additive thermal noise as zero in this dataset
    # alpha is the change metric we wish to estimate in the interval [0, 1]
    # 0 indicates complete change, 1 no change
    vfunc = np.vectorize(add_change)
    for c in range(0, 100):
        if c in range(48, 52):
            arr2[:, c] = vfunc(arr2[:, c])

    da1 = da.from_array(arr1).rechunk((window, window))
    da2 = da.from_array(arr2).rechunk((window, window))
    result = da.map_blocks(local_ccd, da1, da2).compute()

    np.testing.assert_allclose(
            result[:, 10].real, np.ones((100,), dtype=np.float))

    np.testing.assert_allclose(
            result[:, 80].real, np.ones((100,), dtype=np.float))

    np.testing.assert_raises(
        AssertionError,
        np.testing.assert_allclose,
        result[:, 50].real, np.ones((100,)))
