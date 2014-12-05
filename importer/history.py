
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from geoalchemy2 import functions as func
from models.map import Base, Station, Observation, Forecast
from shapely.geometry import Polygon
import argparse
import json


metadata = Base.metadata
engine = create_engine('postgresql://myapp:dbpass@localhost:15432/spatial', echo=True)
Session = sessionmaker(bind=engine)
session = Session()


def import_from_json(data, drop=True):

    if drop:
        Forecast.__table__.drop(engine, checkfirst=True)
        Observation.__table__.drop(engine, checkfirst=True)
        Station.__table__.drop(engine, checkfirst=True)

        Station.__table__.create(engine)
        Observation.__table__.create(engine)
        Forecast.__table__.create(engine)

    for s in data:
        station = Station()
        station.name = s["name"]
        station.dwd_id = s["id"]
        station.altitude = s["altitude"]
        station.geometry = 'SRID=4326;POINT(%s %s)' % (s["longitude"], s["latitude"])
        station.region = list2ewkt(s["region"], 4326)

        session.add(station)

    session.commit()


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