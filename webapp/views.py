from webapp import app, db
from models.map import Country, District, Station
from flask import render_template, request, abort, json


@app.route('/district.json')
def get_district():
    lat = float(request.args.get("lat"))
    lon = float(request.args.get("lon"))
    pt = 'SRID=4326;POINT(%s %s)' % (lon, lat)

    q = db.session.query(District.geometry.ST_AsGeoJSON()).filter(District.geometry.ST_Intersects(pt))
    geojson = q.scalar()

    if not geojson:
        abort(404)

    return geojson


@app.route('/stations.json')
def get_stations():
    stations = db.session.query(Station.region.ST_AsGeoJSON()).filter(Station.region != None).all()
    stations = [json.loads(station[0]) for station in stations]

    return json.jsonify(features=stations)


@app.route('/')
def index():
    return render_template('index.html')