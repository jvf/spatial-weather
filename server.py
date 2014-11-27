from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
engine = create_engine('postgresql://myapp:dbpass@localhost:15432/spatial', echo=True)
Session = sessionmaker(bind=engine)


from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from geoalchemy2 import Geometry
from sqlalchemy import func



Base = declarative_base()
class Admin(Base):
    __tablename__ = 'osm_admin'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    admin_level = Column(Integer)
    geometry = Column(Geometry('POLYGON'))


from flask import Flask, render_template
app = Flask(__name__)


session = Session()

@app.route('/geo.json')
def geo_test():
    admin = session.query(Admin).order_by(Admin.id).first()

    # Geht nicht, weil dieses doofe leaflet nur lat/lon will
    #geojson = session.query(func.ST_AsGeoJSON(Admin.geometry)).order_by(Admin.id).first()
    geojson = session.query(func.ST_AsGeoJSON(func.ST_TRANSFORM(Admin.geometry, 4326))).order_by(Admin.id).first()


    feature = '{{ "type":"Feature", "crs": {{ "type": "name", "properties": {{ "name": "urn:ogc:def:crs:EPSG::3857" }} }}, "geometry": {} }}'.format(geojson[0])
    return feature


@app.route('/')
def hello_world():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
