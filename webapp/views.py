from webapp import app, db
from models.map import Country, State, District, Station, Observation,\
    GFS as Forecast, ContribState, ContribDistrict
from flask import render_template, request, abort, json
from geoalchemy2 import functions as func
from sqlalchemy import func as func1, type_coerce
from datetime import datetime
import time


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/observation/<request_type>.json')
def observation(request_type):
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
        q = db.session.query(District.id,
                             District.name,
                             District.admin_level,
                             District.geometry.ST_AsGeoJSON().label("geometry"),
                             (func1.SUM(Observation.temperature * ContribDistrict.area)
                                    / func1.SUM(ContribDistrict.area))
                                .label("temperature"),
                             (func1.SUM(Observation.rainfall * ContribDistrict.area)
                                    / func1.SUM(ContribDistrict.area))
                                .label("rainfall"),
                             )\
            .filter(Observation.date == request_datetime,
                    #District.geometry.ST_Intersects('SRID=4326;POINT(%s %s)' % (lon, lat)),
                    #State.geometry.ST_Intersects(Station.geometry),
                    District.id == ContribDistrict.district_id,
                    Station.id == ContribDistrict.station_id,
                    Station.id == Observation.station_id,
                    #Observation.rainfall != -999,
                    #Observation.temperature != -999
                    )\
            .group_by(District.id)

        districts = q.all()
        districts = [district._asdict() for district in districts]
        feature_collection = to_feature_collection(districts)

        return json.jsonify(feature_collection)

    elif request_type == "state":
        q = db.session.query(State.id,
                         State.name,
                         State.admin_level,
                         State.geometry.ST_AsGeoJSON().label("geometry"),
                         (func1.SUM(Observation.temperature
                                   * ContribState.area)
                                / func1.SUM(ContribState.area))
                            .label("temperature"),
                         (func1.SUM(Observation.rainfall
                                   * ContribState.area)
                                / func1.SUM(ContribState.area))
                            .label("rainfall"),
                         )\
            .filter(Observation.date == request_datetime,
                    #State.geometry.ST_Intersects('SRID=4326;POINT(%s %s)' % (lon, lat)),
                    #State.geometry.ST_Intersects(Station.geometry),
                    State.id == ContribState.state_id,
                    Station.id == ContribState.station_id,
                    Station.id == Observation.station_id,
                    #Observation.rainfall != -999,
                    #Observation.temperature != -999
                    )\
            .group_by(State.id)

        states = q.all()
        states = [state._asdict() for state in states]
        feature_collection = to_feature_collection(states)

        return json.jsonify(feature_collection)

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
        request_datetime = request_datetime.replace(hour=0, minute=0)

    if request_type == 'station' and not forecast:
        station = db.session.query(Station.dwd_id,
                                   Station.name,
                                   Station.altitude,
                                   Station.geometry.ST_AsGeoJSON().label('geometry'),
                                   Observation.date,
                                   Observation.rainfall,
                                   Observation.temperature) \
            .filter(Observation.station_id == Station.id,
                    Observation.date == request_datetime,
                    func.ST_Intersects(Station.region, 'SRID=4326;POINT(%s %s)' % (lon, lat))) \
            .first()
        if station == None:
            abort(404)

        feature = to_feature(station._asdict())
        return json.jsonify(feature)

    elif request_type == "district":
        q = db.session.query(District.id,
                             District.name,
                             District.admin_level,
                             District.geometry.ST_AsGeoJSON().label("geometry"),
                             (func1.SUM(Observation.temperature * ContribDistrict.area)
                                    / func1.SUM(ContribDistrict.area))
                                .label("mean_temperature"),
                             (func1.SUM(Observation.rainfall * ContribDistrict.area)
                                    / func1.SUM(ContribDistrict.area))
                                .label("mean_rainfall"),
                             )\
            .filter(Observation.date == request_datetime,
                    District.geometry.ST_Intersects('SRID=4326;POINT(%s %s)' % (lon, lat)),
                    #State.geometry.ST_Intersects(Station.geometry),
                    District.id == ContribDistrict.district_id,
                    Station.id == ContribDistrict.station_id,
                    Station.id == Observation.station_id,
                    Observation.rainfall != -999,
                    Observation.temperature != -999
                    )\
            .group_by(District.id)

        response = q.first()
        response = to_feature(response._asdict())
        return json.jsonify(response)

    elif request_type == "state":
        q = db.session.query(State.id,
                             State.name,
                             State.admin_level,
                             State.geometry.ST_AsGeoJSON().label("geometry"),
                             (func1.SUM(Observation.temperature
                                       * ContribState.area)
                                    / func1.SUM(ContribState.area))
                                .label("mean_temperature"),
                             (func1.SUM(Observation.rainfall
                                       * ContribState.area)
                                    / func1.SUM(ContribState.area))
                                .label("mean_rainfall"),
                             )\
            .filter(Observation.date == request_datetime,
                    State.geometry.ST_Intersects('SRID=4326;POINT(%s %s)' % (lon, lat)),
                    #State.geometry.ST_Intersects(Station.geometry),
                    State.id == ContribState.state_id,
                    Station.id == ContribState.station_id,
                    Station.id == Observation.station_id,
                    Observation.rainfall != -999,
                    Observation.temperature != -999
                    )\
            .group_by(State.id)

        response = q.first()
        response = to_feature(response._asdict())
        return json.jsonify(response)

    else:
        abort(404)


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
