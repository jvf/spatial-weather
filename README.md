
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

# import dwd

python manage.py import_dwd --to_json

imports the recent dwd data into data/weather.json

python manage.py import_dwd --from_json

imports dwd observation data from data/weather.json