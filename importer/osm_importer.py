import os
import subprocess
from sqlalchemy import func
from webapp import app, db
from models.map import Osm_Admin, Osm_Places, Country, State, District, Cities


# assumes an existing db 'spatial' with postgis extension

# assumes mapping file in /vagrant/mapping.json
mapping = os.path.abspath('importer' + os.path.sep + 'mapping.json')

# assumes pbf file in /vagrant/data/
pbf = os.path.abspath('data' + os.path.sep + 'germany-latest.osm.pbf')

# assumes imposm3 in importer/
imposm_dir = os.path.abspath('importer')


def run(imposm, load, drop_tables):

    # import from pbf file with imposm
    if imposm:
        import_from_pbf()

    if load:
        # osm_admin -> country
        create_from_admin(Country, 2)

        # osm_admin -> state
        create_from_admin(State, 4)

        # osm_admin -> district
        create_from_admin(District, 6)

        # osm_places -> cities
        create_cities()

        db.session.commit()

    # drop the imposm tables
    if drop_tables:
        Osm_Admin.__table__.drop(db.engine, checkfirst=True)
        Osm_Places.__table__.drop(db.engine, checkfirst=True)


def import_from_pbf():

    connection = 'postgis://' + app.config['DB_USER'] + ':' + app.config['DB_PW'] + '@' + app.config['DB_HOST'] + ':' \
                 + str(app.config['DB_PORT']) + '/' + app.config['DB_NAME']
    os.environ["PATH"] += ":" + imposm_dir
    print(os.environ["PATH"])
    try:
        subprocess.check_call(['imposm3',
                               'import -overwritecache -connection ' + connection + ' -mapping ' + mapping + ' -read ' + pbf + ' -write'])
        subprocess.check_call(
            ['imposm3', 'import -connection ' + connection + ' -mapping ' + mapping + ' -deployproduction'])
    except subprocess.CalledProcessError as e:
        print(e)
        print('Import not possible, aborting')
        exit(1)


def create_from_admin(model, admin_level):
    query = db.session.query(Osm_Admin).filter(Osm_Admin.admin_level == admin_level).all()
    model.__table__.drop(db.engine, checkfirst=True)
    model.__table__.create(db.engine)
    for row in query:
        newEntity = model(name=row.name, osm_id=row.osm_id, type=row.type, admin_level=row.admin_level,
                          geometry=func.ST_Transform(row.geometry, 4326))
        db.session.add(newEntity)

    # for Berlin and Hamburg, add Stadtteile as districts
    if model is District:
        berlin = db.session.query(Osm_Admin).filter_by(admin_level=4, name='Berlin').first()
        hamburg = db.session.query(Osm_Admin).filter_by(admin_level=4, name='Hamburg').first()
        result = db.session.query(Osm_Admin).filter_by(admin_level=9).filter(berlin.geometry.ST_Union(hamburg.geometry).ST_Intersects(Osm_Admin.geometry)).all()
        for row in result:
            db.session.add(District(name=row.name, osm_id=row.osm_id, type=row.type, admin_level=row.admin_level,
                                 geometry=row.geometry.ST_Transform(4326)))


def create_cities():
    query = db.session.query(Osm_Places).all()
    Cities.__table__.drop(db.engine, checkfirst=True)
    Cities.__table__.create(db.engine)
    for place in query:
        new_city = Cities(name=place.name, osm_id=place.osm_id, type=place.type, z_order=place.z_order,
                          population=place.population, geometry=func.ST_Transform(place.geometry, 4326))
        db.session.add(new_city)
