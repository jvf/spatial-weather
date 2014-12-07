# -*- coding: utf-8 -*-

import os
import zipfile
import csv
import json
import ftplib
import numpy as np
from io import BytesIO, TextIOWrapper
from datetime import datetime
from shapely.geometry import Point, Polygon, MultiPolygon
from scipy.spatial import Voronoi
from geoalchemy2 import WKTElement
from webapp import db

"""

Importer for DWD observations (adapted from https://github.com/cholin/spatial/tree/master/scripts)

The [german weather service](http://www.dwd.de) provides a daily observation of
weather in Germany. You can download this data from the following url:

  <ftp://ftp.dwd.de/pub/CDC/observations_germany/climate/daily/kl/>

To be able to import weather data by stations this import script can be useful.

You can limit the imported data with `limit` argument .

Implementation details
----------------------

The importer downloads the station summary file to get a list of all weather
stations. After that it downloads for each station the corresponding zip file
(with measurement data), extracts it in-memory and parses it. To get
information about which weather station is the nearest for a given point, it
also calculates a region polygon for each station. This is done by computing the
voronoi diagram for all stations. The resulting regions may be outside of the
country germany. To avoid this there is a polygon of the border of germany
(from osm data). For each region we calculate the
intersection with this polygon and use the result as final region
(Multi)Polygon.

"""

DEFAULT_HOST = 'ftp.dwd.de'
DEFAULT_PATH = 'pub/CDC/observations_germany/climate/daily/kl/recent/'
DEFAULT_FILE_NAME = 'data/weather.json'

class DWD_Importer:

    def __init__(self, host, path):
        self.host = host
        self.path = path
        self.ftp = ftp_connect(self.host)
        self.stations = []

    def do_import(self, limit = None):
        print("Importing from %s (%s)\n" % (self.host, self.path))
        # station file is iso8859 encoded
        data = self._get_stations_raw(self.path).decode("iso-8859-1").encode("utf-8")

        # parse stations, download each zip, unpack it and parse data
        print("Parsing data...")
        for i, station in enumerate(self._parse_stations(data, limit)):
            print("\t%d. %s " % (i+1, station.name))
            self.stations.append(station)
        print("Parsing done.\n")

        # generate voronoi diagram to generate region polygon for each station
        self._generate_voronoi()
        regions = len([x.region for x in self.stations if x.region is not None])
        print("Generated voronoi diagram (%d regions).\n" % regions)

        # yield parsed stations
        for station in self.stations:
            yield station

        print("\n==> imported %d stations" % len(self.stations))


    def _get_stations_raw(self, path):
        """ get stations file from ftp """
        files = list(ftp_list(self.ftp, path))
        stations_file = [f.strip() for f in files if f.endswith('.txt')][0]
        return ftp_get_file(self.ftp, stations_file).getvalue()

    def _parse_stations(self, data, limit = None):
        # first two lines do not contain data
        lines = data.decode('utf-8').split('\r\n')[2:-1]
        reader = csv.reader(lines, delimiter=' ', skipinitialspace=True)
        i = 0
        for row in reader:
            try:
                station = self._parse_station(row)
                if len(station.measurements) > 0:
                    yield self._parse_station(row)
                    i += 1
                if limit is not None and i >= int(limit):
                    raise StopIteration
            except IndexError:
                pass

    def _parse_station(self, raw):
        coords = Point(float(raw[5]), float(raw[4]))
        station = Station(raw[0], raw[6], coords, raw[3], raw[1], raw[2])
        station.measurements = self._parse_measurements(station)
        return station

    def _parse_measurements(self, station):
        try:
            fp = ftp_get_file(self.ftp, station._get_file_name('recent'))
        except:
            return []

        data = BytesIO()
        with zipfile.ZipFile(fp) as archive:
            # get file name for data
            name = ([x for x in archive.namelist() if x.startswith('produkt_klima_Tageswerte')])[0]
            # extract file into data
            data = archive.open(name)
            data = TextIOWrapper(data)
            # data.decode('utf-8')

        # return all measurement values
        reader = list(csv.reader(data, delimiter=';', skipinitialspace=True))[1:-1]
        return [Measurement(row[1], row[3], row[5], row[13], row[14], row[15]) for row in reader]

    def _generate_voronoi(self):
        # get all lat/long tuples for every station
        points = np.zeros((len(self.stations), 2))
        for i,s in enumerate(self.stations):
            points[i,:] = list(s.coords.coords)[0]

        # generate voronoi and get polygons for each region
        vor = Voronoi(points)
        polygons = []
        for region in vor.regions:
            polygons.append(vor.vertices[region] if -1 not in region else [])

        # load germany border polygon (for intersection test)
        script_path = pbf = os.path.abspath('data')
        path = os.path.join(script_path, 'germany_border.geojson')
        with open(path, "r") as f:
            raw = json.load(f)
            coordinates_ger = raw['features'][0]['geometry']['coordinates']
            polygons_ger = [[p[0], []] for p in coordinates_ger]
            germany = MultiPolygon(polygons_ger)

        # save each voronoi region polygon
        for i, p in enumerate(vor.point_region):
            if len(polygons[p]) > 0:
                # add first point as last point (needed for postgis)
                polygon = Polygon(np.append(polygons[p], [polygons[p][0]], axis=0))

                # limit polygons to border of germany
                polygon_shaped = polygon.intersection(germany)

                # save it
                self.stations[i].region = polygon_shaped


class Station:
    def __init__(self, identifier, name, coords, altitude, date_start, date_end):
        self.identifier = int(identifier)
        self.name = name
        self.altitude = int(altitude)
        self.date_start = date_start
        self.date_end = date_end
        self.measurements = []
        self.coords = coords
        self.region = None

    def to_dict(self):
        return {
            'id' : self.identifier,
            'name': self.name,
            'altitude' : self.altitude,
            'coords' : self.coords.wkt,
            'date_start' : self.date_start,
            'date_end' : self.date_end,
            'region' : self.region.wkt if self.region is not None else None,
            'measurements' : map(lambda x: x.to_dict(), self.measurements)
        }

    def __repr__(self):
        return "Station(name=%s)" % self.name

    def _get_id_as_str(self):
        return '%05d' % self.identifier

    def _get_file_name(self, version):
        values = {
            'recent' : ('tageswerte', 'KL', self._get_id_as_str(), 'akt.zip'),
            'historical' : ('tageswerte', self._get_id_as_str(), self.date_start, self.date_end, 'hist.zip'),
        }
        return '_'.join(values[version])


class Measurement:
    def __init__(self, date_raw, temperature, cloudy, rainfall, sunshine_duration, snowfall_height):
        self.date = datetime.strptime(date_raw, '%Y%m%d')
        self.temperature = temperature
        self.cloudy = cloudy
        self.rainfall = rainfall
        self.sunshine_duration = sunshine_duration
        self.snowfall_height = snowfall_height

    def to_dict(self):
        return {
            'date' : self.date.strftime('%Y-%m-%d'),
            'temperature' : self.temperature,
            'cloudy': self.cloudy,
            'rainfall': self.rainfall,
            'sunshine_duration' : self.sunshine_duration,
            'snowfall_height' : self.snowfall_height
        }

    def __repr__(self):
        return "Measurement(date=%s)" % self.date


def ftp_connect(host):
    ftp = ftplib.FTP(host)
    ftp.login()
    return ftp


def ftp_list(ftp, path):
    ftp.cwd(path)
    ls = []
    ftp.retrlines('MLSD', ls.append)
    return ((entry.split(';')[-1]) for entry in ls)


def ftp_get_file(ftp, path):
    memfile = BytesIO()
    ftp.retrbinary('RETR %s' % path, memfile.write)
    return memfile


def drop_tables():
    from models.map import Station, Observation, Forecast
    Forecast.__table__.drop(db.engine, checkfirst=True)
    Observation.__table__.drop(db.engine, checkfirst=True)
    Station.__table__.drop(db.engine, checkfirst=True)
    Station.__table__.create(db.engine)
    Observation.__table__.create(db.engine)


def import_dwd_db(host=DEFAULT_HOST, path=DEFAULT_PATH, limit=None):
    from models.map import Station, Observation

    drop_tables()
    importer = DWD_Importer(host, path)
    stations = importer.do_import(limit)
    for station in stations:
        geom = WKTElement(station.coords.wkt, srid=4326) if station.coords is not None else None
        region = WKTElement(station.region.wkt, srid=4326) if station.region is not None else None
        obj = Station(
            dwd_id=station.identifier,
            name=station.name,
            altitude=station.altitude,
            geometry=geom,
            region=region)

        for m in station.measurements:
            o = Observation(date=m.date, rainfall=m.rainfall, temperature=m.temperature)
            obj.observations.append(o)
        db.session.add(obj)
        db.session.commit()

        print("%s: %d" % (station.name, len(station.measurements)))


def import_dwd_json(host=DEFAULT_HOST, path=DEFAULT_PATH, file=DEFAULT_FILE_NAME, limit=None):
    importer = DWD_Importer(host, path)
    for station in importer.do_import(limit):
        print("Added %s (%d measurements)" % (station.name, len(station.measurements)))

    with open(file, 'w') as f:
        data = []
        for station in importer.stations:
            station_dict = station.to_dict()
            station_dict['measurements'] = [measurement for measurement in station_dict['measurements']]
            data.append(station_dict)
        json.dump(data, f, sort_keys=True, indent=4, ensure_ascii=False)


def import_dwd_from_json(data, drop=True):
    from models.map import Station, Observation, Forecast
    if drop:
        Forecast.__table__.drop(db.engine, checkfirst=True)
        Observation.__table__.drop(db.engine, checkfirst=True)
        Station.__table__.drop(db.engine, checkfirst=True)

        Station.__table__.create(db.engine)
        Observation.__table__.create(db.engine)
        Forecast.__table__.create(db.engine)

    for s in data:
        print("Importing ", s["name"])
        station = Station()
        station.name = s["name"]
        station.dwd_id = s["id"]
        station.altitude = s["altitude"]
        station.geometry = 'SRID=4326; %s' % s["coords"]
        station.region = list2ewkt(s["region"], 4326)
        for measurement in s['measurements']:
            observation = Observation()
            observation.date = measurement['date']
            observation.rainfall = measurement['rainfall']
            observation.temperature = measurement['temperature']
            station.observations.append(observation)
        db.session.add(station)
        db.session.commit()


def list2ewkt(items, srid=4326):
    if items is None:
        return 'SRID=%s;POLYGON EMPTY"' % (srid)
    else:
        return 'SRID=%s; %s' % (srid, items)