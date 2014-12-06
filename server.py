from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.map import Country, District, Station
from flask import Flask, render_template, request, abort, json

engine = create_engine('postgresql://myapp:dbpass@localhost:15432/spatial', echo=True)
Session = sessionmaker(bind=engine)
app = Flask(__name__)
app.config.from_pyfile('config.py')
session = Session()

@app.route('/district.json')
def get_district():
    lat = float(request.args.get("lat"))
    lon = float(request.args.get("lon"))
    pt = 'SRID=4326;POINT(%s %s)' % (lon, lat)

    q = session.query(District.geometry.ST_AsGeoJSON()).filter(District.geometry.ST_Intersects(pt))
    geojson = q.scalar()

    if not geojson:
        abort(404)

    return geojson

@app.route('/stations.json')
def get_stations():
    stations = session.query(Station.region.ST_AsGeoJSON()).all()
    stations = [json.loads(station[0]) for station in stations]

    return json.jsonify(features=stations)


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)