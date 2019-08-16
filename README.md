# SAR-TileDB

A Python 3 (tested with 3.6) library for simple processing of interferometric SAR (INSAR) data.

## Installation

The preferred installation is with Conda.

Currently TileDB and GDAL need to be installed from source.

Install [TileDB](https://github.com/TileDB-Inc/TileDB).

Install GDAL from conda

```
conda create -n gdal3 gdal=3
```

or from source

```
./configure --with-tiledb --with-libtiff=internal --prefix=/usr/local --with-curl=no --with-crypto=no --with-openssl=no --with-python
```

Install additional dependencies

```
conda create --name insar python=3.6
conda activate insar
conda install -c anaconda numpy
conda install -c anaconda cython
conda install dask
conda install -c conda-forge dask-image
conda install xarray
conda install -c conda-forge tiledb-py
```

Now build RasterIO within the conda environment

```
git clone git@github.com:mapbox/rasterio.git
cd rasterio
python setup.py install
```

If you intend to use the flight path tools then install Fiona from source;

```
git clone git@github.com:Toblerity/Fiona.git
cd Fiona
python setup.py install
```

We are currently patching `dask/array/tiledb_io.py`, this will be merged into dask.

```
@@ -145,9 +145,8 @@ def to_tiledb(
     elif isinstance(uri, tiledb.Array):
         tdb = uri
         # sanity checks
-        if not (
-            (darray.shape == tdb.shape)
-            and (darray.dtype == tdb.dtype)
+        if not ( 
+            (darray.dtype == tdb.dtype)
             and (darray.ndim == tdb.ndim)
         ):
             raise ValueError(
```

Install sar-stack command line plugin

```
cd SAR-TileDB
pip install -e .
rio stack-sar --help
```

## Test

`python -m pytest .`


## CLI Usage

UAVSAR data is available from https://uavsar.jpl.nasa.gov/

Note the output stack is in the slant range projection. It is possible to assign approximate geo-referencing from the output of the `flight-path` tool described below.

1. stack-sar usage

`rio stack-sar --help`

2. Create a UAVSAR stack and run change detection algorithm

`
rio stack-sar --type uavsar ./data/Haywrd_23501_09006_012_090218_L090HH_02_BC_s1_1x1.slc ./data/Haywrd_23501_09092_001_091119_L090HH_02_BC_s1_1x1.slc --output stack_arr --type uavsar --bbox 0 0 8000 8000
`

3. process-stack usage

`rio process-stack --help`

4. Run processing algorith on existing stack

`rio process-stack --function ccd --bands 0 1 --output result stack_arr`

5. flight-path usage

`rio flight-path --help`

6. Create flight path from UAVSAR metadata

`
 rio flight-path -t uavsar lathrop/SDelta_15503_04_BC_s3_2x8.llh | fio collect > path.geojson
`

7. View Dask processing status

`open http://localhost:8787/status`
