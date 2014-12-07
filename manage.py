from flask.ext.script import Manager
from webapp import app
from importer.osm_importer import run as osm_import
from importer.dwd_importer import import_dwd_db, import_dwd_json, import_dwd_from_json
from models.map import Osm_Admin, Osm_Places, Station, Observation, Country, State, District, Cities
from webapp import db
import os
import json

manager = Manager(app)

@manager.option('-b, --bool', dest='test', help="bool", default=False, required=False, metavar="foobar")
def test(test):
    "test command"
    print(test)


@manager.option('--imposm', action='store_true', dest='imposm', default=False,
                help="import data with imposm3 from pfb file")
@manager.option('--load', action='store_true', dest='load', default=False,
                help="create map tables for the app from the tables created by imposm")
@manager.option('--drop_tables', action='store_true', dest='drop_tables', default=False,
                help="drop the osm_admin and osm_places tables from the imposm import")
def import_osm(imposm, load, drop_tables):
    "import data osm map data from pbf file"
    # print("imposm: %s. load: %s" % (imposm, load))
    osm_import(imposm, load, drop_tables)


@manager.option('-t', '--tables', dest='tables', help="osm, map, dwd, gfs", required=True)
def drop_tables(tables):
    "drop the tables for osm (osm_admin, osm_places), map (country, state, district, cities) or dwd (station, observation)"

    if tables == 'osm':
        Osm_Admin.__table__.drop(db.engine, checkfirst=True)
        Osm_Places.__table__.drop(db.engine, checkfirst=True)
    elif tables == 'map':
        Country.__table__.drop(db.engine, checkfirst=True)
        State.__table__.drop(db.engine, checkfirst=True)
        District.__table__.drop(db.engine, checkfirst=True)
        Cities.__table__.drop(db.engine, checkfirst=True)
    elif tables == 'dwd':
        db.session.query(Observation).delete()
        db.session.query(Station).delete()
        db.session.commit()
        Observation.__table__.drop(db.engine, checkfirst=True)
        Station.__table__.drop(db.engine, checkfirst=True)


DEFAULT_FILE_NAME = 'data/weather.json'
@manager.option('--to_json', action='store_true', dest='to_json', default=False,
                help="import data to json")
@manager.option('--load_from_json', action='store_true', dest='load_from_json', default=False,
                help="import from json file")
# @manager.option('--drop_tables', action='store_true', dest='drop_tables', default=False,
#                 help="drop the osm_admin and osm_places tables from the imposm import")
def import_dwd(to_json, load_from_json, file=DEFAULT_FILE_NAME):
    if to_json:
        if os.path.isfile(file):
            override = input('%s already exists. Override? [y/N]' % file)
            if override == 'y' or override == 'yes':
                print("overriding ", file)
            else:
                print("aborting...")
                return
        import_dwd_json(limit=3)
    elif load_from_json:
        data = json.load(open(file, 'r'))
        import_dwd_from_json(data)
    else:
        import_dwd_db()

if __name__ == "__main__":
    manager.run()