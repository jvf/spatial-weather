
## Installation and Setup

It is strongly advised to install scipy, numpy and shapely (globaly) as binary
packages and not through virtualenv, because of their large number of non-python
dependencies. E.g. on Debian/Ubuntu systems use
    `sudo apt-get install python3-numpy python3-scipy python3-shapely`
to install. Make sure access to the global packages is activated in the virtual
environment (e.g. through `toggleglobalsitepackages` in `virtualenvwrapper`).

When compiling entirely from source, You also might need to install the following
libraries: (for shapely): libgeos-dev; (for scipy): libblas-dev, liblapack-dev,
gfortran.

# Import OSM Data

Imports the OSM data for Germany. The following tables are created: Country, State, District and Cities. The data is
imported from `germany-latest.osm.pbf`, obtained from [geofabrik](http://www.geofabrik.de). The pbf file needs to be placed in `data/`.

The importer used is `imposm3`, which is included in the vagrant setup (and will be executed within the VM). The import
uses a custem mapping, which is provided in `importer/mapping.json`. The import is conducted in two steps: First, the
data is imported to the tables Osm_Admin and Osm_Places. Second the Country, State, District and Cities tables are created
from these tables.


## Usage

To import all the OSM data use the manage script. To invoke the whole pipeline use the following command:

`python manage.py import_osm --imposm --load --drop_tables `

* `--imposm` the first import step (see above)
* `--load` the second import step (see above)
* `--drop-tables` deletes the Osm_Admin and Osm_Places tables after a successful import
    
All the above steps can be invoked separately.

DYLD_LIBRARY_PATH=/Applications/Postgres.app/Contents/Versions/9.3/lib python manage.py drop_tables -t osm

## Mac OS X
```
python manage.py import_osm --drop_tables --imposm --load
DYLD_LIBRARY_PATH=/Applications/Postgres.app/Contents/Versions/9.3/lib python manage.py import_osm --drop_tables --load
```

# Import DWD Data

Imports weather observation data from the DWD (Deutscher Wetterdienst). The importer is a adopted version from
[cholin](https://github.com/cholin/fuberlin_spatial_db_project). Per default, it downloads all the [recent daily observations]
(ftp://ftp.dwd.de/pub/CDC/observations_germany/climate/daily/kl).

Details on the importer from [cholin](https://github.com/cholin/fuberlin_spatial_db_project/blob/master/scripts/dwd/README.md):

> The importer downloads the station summary file to get a list of all weather stations. After that it downloads for each
station the corresponding zip file (with measurement data), extracts it in-memory and parses it. To get information about
which weather station is the nearest for a given point, it also calculates a region polygon for each station. This is done
by computing the voronoi diagram for all stations. The resulting regions may be outside of the country germany. To avoid
this there is a polygon of the border of germany (data is from naturalearthdata.com - country extraction and exportation
as geojson with qgis). For each region we calculate the intersection with this polygon and use the result as final region
(Multi)Polygon.

## Usage

Use the importer with the `manage.py` script:

To download all data and import all observation data:

`python manage.py import_dwd`

Create an intermediate result in `data/weather.json`:

`python manage.py import_dwd --to_json`

Import the intermediate result from `data/weather.json`:

`python manage.py import_dwd --from_json`

## Mac OS X
```
python manage.py import_dwd --to_json
DYLD_LIBRARY_PATH=/Applications/Postgres.app/Contents/Versions/9.3/lib ython manage.py import_dwd --from_json
```

# Download and Import NOAA GFS Data (Forecasts)
Importing the Forecast Data is done in two steps. First you have to download the GRIB files from the NOAA FTP servers. Then you have to import them as Postgis Raster.

## Download
For downloading the GFS data a date range and a target directory has to be specified. The format for the start and enddate is `YYYYMMDDHH` or `latest` for the most recently available GFS calculation.
Optionally the forecast hours can be specified as a range (Defaults to download from 0 to 129 in 3 hour steps).

```
usage: run_gfs.py download [-h] [--hours_start HOURS_START]
                           [--hours_stop HOURS_STOP] [--hours_step HOURS_STEP]
                           [startdate] [enddate] datadir
```

For example, assuming data should be stored to `data/forecasts`:

`./run_gfs.py 2014121112 2015011306 download data/forecasts`

## Import
To import the downloaded data, the download directory and a data range has to be specified: 

```
usage: run_gfs.py import [-h] datadir [startdate] [enddate]
```

For example, assuming the data is stored in `data/forecasts`:

`./run_gfs.py import data/forecasts 2014121112 2015011306`

## Build Contrib Tables

To speed up some queries, the area contribution of the region (voronoi cell) of weather stations to states and districts is precomputed and materialized. Run ```python manage.py calculate_contrib_area``` to create and fill the ContribState and ContribDistrict tables.


# Troubleshooting


## Mac OS X

### UnicodeEncodeError

Python inherist the standard locale from the current shell environment. If this is not set to utf8 it tries to convert
to ASCII, which produces. `UnicodeEncodeError: 'ascii' codec can't encode character`
Test with `$ locale`, this should show utf-8. If not, fix with
```
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
```

### libssl / libcrypto Error from psycopq

The `libssl` version Mac OS X uses might be too old for `psycopg`, resulting in an error like the following:

```
...
ImportError: dlopen(...lib/python3.4/site-packages/psycopg2/_psycopg.so, 2): Library not loaded: libssl.1.0.0.dylib
  Referenced from: ...lib/python3.4/site-packages/psycopg2/_psycopg.so
  Reason: image not found
```

This can be solved by changing the dynamic shared library install names in the `psycopq` binary. First, find out the version `psycopq` is using:

```
otool -L /Users/jvf/miniconda3/envs/env-sw/lib/python3.4/site-packages/psycopg2/_psycopg.so
$ /Users/jvf/miniconda3/envs/env-sw/lib/python3.4/site-packages/psycopg2/_psycopg.so:
	/usr/local/lib/libpq.5.dylib (compatibility version 5.0.0, current version 5.6.0)
	libssl.1.0.0.dylib (compatibility version 1.0.0, current version 1.0.0)
	libcrypto.1.0.0.dylib (compatibility version 1.0.0, current version 1.0.0)
	/usr/lib/libSystem.B.dylib (compatibility version 1.0.0, current version 1213.0.0)
	/usr/lib/libgcc_s.1.dylib (compatibility version 1.0.0, current version 283.0.0)
```

Now, change the the shared libraries for `libssl` and `libcrypto` (using the libraries provided by [Postgres.app](http://postgresapp.com)):

```
install_name_tool -change libssl.1.0.0.dylib /Applications/Postgres.app/Contents/Versions/9.3/lib/libssl.1.0.0.dylib /Users/jvf/miniconda3/envs/env-sw/lib/python3.4/site-packages/psycopg2/_psycopg.so
install_name_tool -change libcrypto.1.0.0.dylib /Applications/Postgres.app/Contents/Versions/9.3/lib/libcrypto.1.0.0.dylib /Users/jvf/miniconda3/envs/env-sw/lib/python3.4/site-packages/psycopg2/_psycopg.so
```



`psycopq` now uses the correct libraries:

```
otool -L /Users/jvf/miniconda3/envs/env-sw/lib/python3.4/site-packages/psycopg2/_psycopg.so                                                                                                                                                   
$ /Users/jvf/miniconda3/envs/env-sw/lib/python3.4/site-packages/psycopg2/_psycopg.so:
	/usr/local/lib/libpq.5.dylib (compatibility version 5.0.0, current version 5.6.0)
	/Applications/Postgres.app/Contents/Versions/9.3/lib/libssl.1.0.0.dylib (compatibility version 1.0.0, current version 1.0.0)
	/Applications/Postgres.app/Contents/Versions/9.3/lib/libcrypto.1.0.0.dylib (compatibility version 1.0.0, current version 1.0.0)
	/usr/lib/libSystem.B.dylib (compatibility version 1.0.0, current version 1213.0.0)
	/usr/lib/libgcc_s.1.dylib (compatibility version 1.0.0, current version 283.0.0)
```

It is strongly recommended to do all this in an virtual environment to not mess up your system!

Source: More Information: [superuser.com](http://superuser.com/a/721564)


Another possibilty is to prefix commands with `DYLD_LIBRARY_PATH` and `DYLD_FRAMEWORK_PATH`, but this works less reliable and potentially messes up the linking of other libraries. Example:

```
DYLD_LIBRARY_PATH=$(HOME)/lib:/usr/local/lib:/lib:/usr/lib:/Applications/Postgres.app/Contents/Versions/9.3/lib,DYLD_FRAMEWORK_PATH=/Library/Frameworks:/Network/Library/Frameworks:/System/Library/Frameworks python manage.py import_dwd
```

 providing an alternative path for a newer version of `libssl` to the dynamic linker (in this example the libs from [Postgres.app](http://postgresapp.com) are used, but can link against a `homebrew` installed version as well):

```
export DYLD_LIBRARY_PATH=$(HOME)/lib:/usr/local/lib:/lib:/usr/lib:/Applications/Postgres.app/Contents/Versions/9.3/lib
export DYLD_FRAMEWORK_PATH=/Library/Frameworks:/Network/Library/Frameworks:/System/Library/Frameworks
```

Source: [stackoverflow.com](http://stackoverflow.com/questions/11365619/psycopg2-installation-error-library-not-loaded-libssl-dylib)




