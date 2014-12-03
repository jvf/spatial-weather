from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.map import Country, District
from flask import Flask, render_template, request, abort

engine = create_engine('postgresql://myapp:dbpass@localhost:15432/spatial', echo=True)
Session = sessionmaker(bind=engine)
app = Flask(__name__)
session = Session()


@app.route('/geo.json')
def geo_test():
    geojson = session.query(District.geometry.ST_AsGeoJSON()).filter_by(name='Neukölln').first()
    if not geojson:
        abort(404)
    return geojson


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


@app.route('/point.json')
def get_point():
    lat = float(request.args.get("lat"))
    lon = float(request.args.get("lon"))
    pt = 'SRID=4326;POINT(%s %s)' % (lon, lat)

    q = session.query(pt.ST_AsGeoJSON())
    geojson = q.scalar()
    return geojson



@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
