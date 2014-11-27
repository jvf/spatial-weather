from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
engine = create_engine('postgresql://myapp:dbpass@localhost:15432/spatial', echo=True)
Session = sessionmaker(bind=engine)


from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from geoalchemy2 import Geometry
#from sqlalchemy import func, select
from sqlalchemy import func as fun2
from geoalchemy2.functions import ST_Intersects
from geoalchemy2 import functions as func

import pyproj
projections = {
    3857: pyproj.Proj("+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs"),
    4326: pyproj.Proj("+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs ")
}


def transform(srid1, srid2, x, y, z=None, radians=False):
    return pyproj.transform(projections[srid1], projections[srid2],
                            x, y, z, radians)


from geoalchemy2 import elements
class Point(elements.WKTElement):
    wkt_tpl = "POINT ({} {})"

    def __init__(self, lon, lat, srid):
        self.lon = lon
        self.lat = lat

        data = self.wkt_tpl.format(lon, lat)
        elements.WKTElement.__init__(self, data, srid=srid)

    def transform(self, srid):
        lon, lat = transform(self.srid, srid, self.lon, self.lat)
        return Point(lon, lat, srid)



Base = declarative_base()
class Admin(Base):
    __tablename__ = 'osm_admin'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    admin_level = Column(Integer)
    geometry = Column(Geometry('POLYGON', srid=3857))


from flask import Flask, render_template, request, abort
app = Flask(__name__)


session = Session()

@app.route('/geo.json')
def geo_test():
    admin = session.query(Admin).order_by(Admin.id).first()

    # Geht nicht, weil dieses doofe leaflet nur lat/lon will
    #geojson = session.query(func.ST_AsGeoJSON(Admin.geometry)).order_by(Admin.id).first()
    geojson = session.query(func.ST_AsGeoJSON(func.ST_Transform(Admin.geometry, 4326))).order_by(Admin.id).first()
    return geojson

    # Es muss gar kein Feature sein
    # feature = '{{ "type":"Feature", "crs": {{ "type": "name", "properties": {{ "name": "urn:ogc:def:crs:EPSG::3857" }} }}, "geometry": {} }}'.format(geojson[0])
    # return feature

@app.route('/district.json')
def get_district():
    lat = float(request.args.get("lat"))
    lon = float(request.args.get("lon"))

    pt = Point(lon, lat, 4326)
    pt2 = pt.transform(3857)

    q = session.query(Admin.geometry.ST_Transform(4326).ST_AsGeoJSON())\
        .filter(Admin.geometry.ST_Intersects(pt2),
                Admin.admin_level == 10)
    geojson = q.scalar()

    if not geojson:
        abort(404)

    return geojson


@app.route('/point.json')
def get_point():
    lat = float(request.args.get("lat"))
    lon = float(request.args.get("lon"))
    pt = Point(lon, lat, 4326)

    #q = session.query(fun2.ST_AsGeoJSON(fun2.ST_Transform(fun2.ST_SetSRID(fun2.ST_POINT(x, y), 3857), 4326)))
    q = session.query(pt.ST_Transform(4326).ST_AsGeoJSON())
    geojson = q.scalar()
    return geojson



@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
