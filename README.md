# SAR-TileDB

A Python 3 (tested with 3.6) library for simple processing of interferometric SAR (INSAR) data.

## Installation

The preferred installation is with Conda.

Currently TileDB and GDAL need to be installed from source.

Install [TileDB](https://github.com/TileDB-Inc/TileDB).

Install the current master of GDAL at the system level (tested with sha - 26870845456955237e56a94f496ec493bc226863) with the TileDB driver (this step will be replaced with conda).

```
./configure --with-tiledb --with-libtiff=internal --prefix=/usr/local --with-curl=no --with-crypto=no --with-openssl=no --with-python
```

```
conda create --name insar python=3.6
conda activate insar
conda install -c anaconda numpy
conda install -c anaconda cython
```

Now build RasterIO for within the conda environment

```
git clone git@github.com:TileDB-Inc/rasterio.git
cd rasterio
git checkout gdal3
python setup.py install
```

Install sar-stack command line plugin

```
cd SAR-TileDB
pip install -e .
rio stack-sar --help
```
