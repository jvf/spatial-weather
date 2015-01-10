from webapp import app, db
from models.map import Country, State, District, Station, Observation, GFS as Forecast
from flask import render_template, request, abort, json
from geoalchemy2 import functions as func
from sqlalchemy import func as func1, type_coerce
from datetime import datetime
import time


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
def dummy(path):
    return app.send_static_file("lander.geojson")


@app.route('/observation/<request_type>.json')
def fancyfunctionname(request_type):
    request_datetime = datetime.strptime(request.args.get("datetime", 0000000000), "%Y%m%d%H")

    if request_type == 'station':
        # TODO: filter germany
        stations = db.session.query(Station.dwd_id, Station.name, Station.altitude,
                                    Station.region.ST_AsGeoJSON().label('geometry'), Observation.date,
                                    Observation.rainfall, Observation.temperature) \
            .filter(Observation.station_id == Station.id, Observation.date == request_datetime) \
            .all()

        stations = [station._asdict() for station in stations]
        feature_collection = to_feature_collection(stations)

        return json.jsonify(feature_collection)

    elif request_type == "district":
        abort(404)
    elif request_type == "state":
        abort(404)

    abort(404)


@app.route('/info/<request_type>.json')
def info(request_type):
    """ example queries:
        http://127.0.0.1:5000/info/station.json?lon=8.237&lat=52.9335&forecast=False&datetime=2014120100
        http://127.0.0.1:5000/info/district.json?lon=10.237&lat=52.9335&forecast=False&datetime=2014120100
        http://127.0.0.1:5000/info/district.json?lon=9.237&lat=52.9335&forecast=False&datetime=2014120100 (example for no stations in district)
        http://127.0.0.1:5000/info/state.json?lon=13.237&lat=52.435&forecast=False&datetime=201420100
    """
    # todo handle dates without observations properly
    lat = float(request.args.get("lat"))
    lon = float(request.args.get("lon"))
    forecast = request.args.get("forecast") in ['true', 'True']
    # datetime format JJJJMMTTHH (Observation: JJJJMMMTT00)
    request_datetime = datetime.strptime(request.args.get("datetime", 0000000000), "%Y%m%d%H")
    hours = request.args.get("hours", None)  # the number of hours into the future a forecast was made

    # If the data isn't a forecast it should ignore the hours of the datetime (set to 00).
    # TODO: discuss if this should handled at the client
    if not forecast:
        request_datetime = request_datetime.replace(hours=0, minute=0)

    if request_type == 'station' and not forecast:
        station = db.session.query(Station.dwd_id, Station.name, Station.altitude,
                                   Station.geometry.ST_AsGeoJSON().label('geometry'), Observation.date,
                                   Observation.rainfall, Observation.temperature) \
            .filter(Observation.station_id == Station.id, Observation.date == request_datetime,
                    func.ST_Intersects(Station.region, 'SRID=4326;POINT(%s %s)' % (lon, lat))) \
            .first()
        if station == None:
            abort(404)
        feature = to_feature(station._asdict())
        return json.jsonify(feature)

    elif request_type == "district":
        district = District.query.filter(District.geometry.ST_Intersects('SRID=4326;POINT(%s %s)' % (lon, lat))).first()
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
        state = State.query.filter(State.geometry.ST_Intersects('SRID=4326;POINT(%s %s)' % (lon, lat))).first()
        geometry = db.session.scalar(func.ST_AsGeoJSON(state.geometry))

        response_builder = {"name": state.name, "admin_entity": State.__tablename__, "admin_level": state.admin_level,
                            "geometry": geometry, "observations": {}}

        stations = Station.query.filter(Station.geometry.ST_Intersects(state.geometry)).all()
        calc_means(request_datetime, response_builder, stations, state)
        response = to_feature(response_builder)
        return json.jsonify(response)
    else:
        abort(404)


@app.route('/forecast/<request_type>.json')
def forecast(request_type):
    """ example queries:
    http://127.0.0.1:5000/forecast/district.json?datetime=2014121112&hours=6
    http://127.0.0.1:5000/forecast/state.json?datetime=2014121112&hours=3
    http://127.0.0.1:5000/forecast/station.json?datetime=2014121112&hours=9
    """
    # datetime format JJJJMMTTHH (Observation: JJJJMMMTT00)
    request_datetime = datetime.strptime(request.args.get("datetime", 0000000000), "%Y%m%d%H")
    hours = request.args.get("hours", None)  # the number of hours into the future a forecast was made

    if request_type == 'state' or request_type == 'district' or request_type == 'station':
        if request_type == 'state':
            model = State
            geo = State.geometry
        elif request_type == 'district':
            model = District
            geo = District.geometry
        elif request_type == 'station':
            model = Station
            geo = Station.region

        start_time = time.clock()
        forecasts = db.session \
            .query(
                model.name,
                func.ST_AsGeoJSON(geo).label('geometry'),
                func1.ST_SummaryStats(func1.ST_CLIP(Forecast.rast, 1, geo, -999, True), 1, True).label('stats_tmp'),
                # func1.ST_SummaryStats(func1.ST_CLIP(Forecast.rast, 2, geo, -999, True), 1, True).label('stats_tmin'),
                # func1.ST_SummaryStats(func1.ST_CLIP(Forecast.rast, 3, geo, -999, True), 1, True).label('stats_tmax'),
                func1.ST_SummaryStats(func1.ST_CLIP(Forecast.rast, 4, geo, -999, True), 1, True).label('stats_pwat')
            ) \
            .filter(Forecast.rast.ST_Intersects(geo),
                    Forecast.forecast_date == request_datetime,
                    Forecast.forecast_hour == hours) \
            .all()
        print(time.clock() - start_time, "seconds for the query")

        # abort on empty queries (usually due to dates or hours not covered)
        if len(forecasts) == 0:
            abort(404)

        # build the response (FeatureCollection)
        start_time = time.clock()
        features = []

        for f in forecasts:
            response_builder = {'name': f.name, 'type': request_type, 'geometry': f.geometry}

            # unpack summary stats (string of form '(<count>, <sum>, <mean>, <stddev>, <min>, <max>)'
            for i in range(6):
                stats_tmp = f.stats_tmp.replace('(', '').replace(')', '').split(',')
                # stats_tmin = f.stats_tmin.replace('(', '').replace(')', '').split(',')
                # stats_tmax = f.stats_tmax.replace('(', '').replace(')', '').split(',')
                stats_pwat = f.stats_pwat.replace('(', '').replace(')', '').split(',')
                keys = ['count', 'sum', 'mean', 'stddev', 'min', 'max']
                response_builder['tmp_'+keys[i]] = stats_tmp[i]
                # response_builder['tmin_'+keys[i]] = stats_tmin[i]
                # response_builder['tmax_'+keys[i]] = stats_tmax[i]
                response_builder['pwat_'+keys[i]] = stats_pwat[i]

            features.append(to_feature(response_builder))

        # build the feature collection
        feautre_collection = {"type": "FeatureCollection", "features": features}
        print(time.clock() - start_time, "seconds for building the dict")

        # jsonify
        start_time = time.clock()
        response = json.jsonify(feautre_collection)
        print(time.clock() - start_time, "seconds for jsonification")
        return response
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


def to_feature_collection(rows):
    features = [to_feature(row) for row in rows]
    collection = {"type": "FeatureCollection",
                  "features": features}
    return collection


def to_feature(fields):
    feature = {"type": "Feature"}
    properties = {}
    for key, value in fields.items():
        if key == "geometry":
            geom = json.loads(value)
            feature[key] = geom
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
        if observation == None:
            abort(404)

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
    response_builder["date"] = observation.date
