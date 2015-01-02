from webapp import app, db
from models.map import Country, District, Station, Observation
from flask import render_template, request, abort, json
from geoalchemy2 import functions as func
from datetime import datetime


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


@app.route('/forecast/<path:path>')
@app.route('/observation/<path:path>')
def dummy(path):
    return app.send_static_file("lander.geojson")


@app.route('/info/<request_type>.json')
def info(request_type):
    """ example queries:
        http://127.0.0.1:5000/info/station.json?lat=8.237&lon=52.9335&forecast=False&datetime=2014120100
    """
    lat = float(request.args.get("lat"))
    lon = float(request.args.get("lon"))
    forecast = request.args.get("forecast")
    # datetime format JJJJMMTTHH (Observation: JJJJMMMTT00)
    request_datetime = datetime.strptime(request.args.get("datetime", 0000000000), "%Y%m%d%H")
    hours = request.args.get("hours", None)  # the number of hours into the future a forecast was made
    if request_type == 'station' and forecast not in ['true', 'True']:
        station = db.session.query(Station.dwd_id, Station.name, Station.altitude,
                                   Station.geometry.ST_AsGeoJSON().label('geometry'), Observation.date,
                                   Observation.rainfall, Observation.temperature).filter(
            Observation.station_id == Station.id, Observation.date == request_datetime,
            func.ST_Intersects(Station.region, 'SRID=4326;POINT(%s %s)' % (lat, lon))).first()

        feature = to_feature(station._asdict())
        return json.jsonify(feature)
    else:
        return json.jsonify(response="not yet implemented")


@app.route('/stations.json')
def get_stations():
    stations = db.session.query(Station.region.ST_AsGeoJSON()).filter(Station.region != None).all()
    stations = [json.loads(station[0]) for station in stations]

    return json.jsonify(features=stations)


@app.route('/')
def index():
    return render_template('index.html')


def to_feature(fields):
    feature = {"type": "Feature"}
    properties = {}
    for key, value in fields.items():
        if key == "geometry":
            feature[key] = value
        else:
            properties[key] = value

    feature["properties"] = properties
    return feature
