from webapp import app, db
from models.map import Country, State, District, Station, Observation
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
        http://127.0.0.1:5000/info/district.json?lat=10.237&lon=52.9335&forecast=False&datetime=2014120100
        http://127.0.0.1:5000/info/district.json?lat=9.237&lon=52.9335&forecast=False&datetime=2014120100 (example for no stations in district)
        http://127.0.0.1:5000/info/state.json?lat=13.237&lon=52.435&forecast=False&datetime=201420100
    """
    # todo handle dates without observations properly
    lat = float(request.args.get("lat"))
    lon = float(request.args.get("lon"))
    forecast = request.args.get("forecast")
    # datetime format JJJJMMTTHH (Observation: JJJJMMMTT00)
    request_datetime = datetime.strptime(request.args.get("datetime", 0000000000), "%Y%m%d%H")
    hours = request.args.get("hours", None)  # the number of hours into the future a forecast was made
    if request_type == 'station' and forecast not in ['true', 'True']:
        station = db.session.query(Station.dwd_id, Station.name, Station.altitude,
                                   Station.geometry.ST_AsGeoJSON().label('geometry'), Observation.date,
                                   Observation.rainfall, Observation.temperature) \
            .filter(Observation.station_id == Station.id, Observation.date == request_datetime,
                    func.ST_Intersects(Station.region, 'SRID=4326;POINT(%s %s)' % (lat, lon))) \
            .first()

        feature = to_feature(station._asdict())
        return json.jsonify(feature)

    elif request_type == "district":
        district = District.query.filter(District.geometry.ST_Intersects('SRID=4326;POINT(%s %s)' % (lat, lon))).first()
        geometry = db.session.scalar(func.ST_AsGeoJSON(district.geometry))

        response_builder = {"name": district.name, "admin_entity": District.__tablename__,
                            "admin_level": district.admin_level,
                            "geometry": geometry, "observations": {}}

        '''
        intersect between region (voronoi cell) of a station and the district geometry, because there are districts
        which don't have any stations in them, e.g. Landkreis Verden
        '''
        stations = Station.query.filter(Station.region.ST_Intersects(district.geometry)).all()
        calc_means(request_datetime, response_builder, stations, district)

        response = to_feature(response_builder)
        return json.jsonify(response)
    elif request_type == "state":
        state = State.query.filter(State.geometry.ST_Intersects('SRID=4326;POINT(%s %s)' % (lat, lon))).first()
        geometry = db.session.scalar(func.ST_AsGeoJSON(state.geometry))

        response_builder = {"name": state.name, "admin_entity": State.__tablename__, "admin_level": state.admin_level,
                            "geometry": geometry, "observations": {}}

        stations = Station.query.filter(Station.geometry.ST_Intersects(state.geometry)).all()
        calc_means(request_datetime, response_builder, stations, state)
        response = to_feature(response_builder)
        return json.jsonify(response)
    else:
        abort(404)


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


def calc_means(request_datetime, response_builder, stations, admin_entity):
    """
    Calculates the weighted arithmetic mean.
    The mean is weighted by the area a region of a station contributes to the admin_entity.
    """
    mean_temp, mean_rain, weight_temp, weight_rain = 0, 0, 0, 0
    for station in stations:
        observation = Observation.query.filter(Observation.station_id == station.id,
                                               Observation.date == request_datetime).first()
        contributing_area = db.session.scalar(func.ST_Area(func.ST_Intersection(station.region, admin_entity.geometry)))
        # ignore -999 values
        if observation.temperature != -999:
            mean_temp += (observation.temperature * contributing_area)
            weight_temp += contributing_area
        if observation.rainfall != -999:
            mean_rain += (observation.rainfall * contributing_area)
            weight_rain += contributing_area

        # uncomment for debugging
        # response_builder["observations"][station.name] = {"id": observation.id, "date": observation.date,
        #                                                   "temperature": observation.temperature,
        #                                                   "rainfall": observation.rainfall,
        #                                                   "weight": contributing_area}
    response_builder["mean temperature"] = mean_temp / weight_temp
    response_builder["mean rainfall"] = mean_rain / weight_rain