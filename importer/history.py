
from models.map import Station, Observation, Forecast
from webapp import db
from shapely.geometry import Polygon
import argparse
import json


def import_from_json(data, drop=True):

    if drop:
        Forecast.__table__.drop(db.engine, checkfirst=True)
        Observation.__table__.drop(db.engine, checkfirst=True)
        Station.__table__.drop(db.engine, checkfirst=True)

        Station.__table__.create(db.engine)
        Observation.__table__.create(db.engine)
        Forecast.__table__.create(db.engine)

    for s in data:
        station = Station()
        station.name = s["name"]
        station.dwd_id = s["id"]
        station.altitude = s["altitude"]
        station.geometry = 'SRID=4326;POINT(%s %s)' % (s["longitude"], s["latitude"])
        station.region = list2ewkt(s["region"], 4326)

        db.session.add(station)

    db.session.commit()


def list2ewkt(items, srid=4326):
    if not len(items):
        return 'SRID=%s;POLYGON EMPTY"' % (srid)

    # Jaja das ist etwas overkill, ich gebe es ja zu
    p = Polygon(items)
    return 'SRID=%s;%s' % (srid, p.wkt)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("json", type=argparse.FileType('r'))
    args = parser.parse_args()

    data = json.load(args.json)
    import_from_json(data)


if __name__ == "__main__":
    main()