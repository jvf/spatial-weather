import os
import subprocess

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func

from models.map import Osm_Admin, Osm_Places, Country, State, District, Cities, Base



# connection
db_user = 'myapp'
db_pw = 'dbpass'
db_host = 'localhost'
db_port = 15432
db_name = 'spatial'  # assumes an existing db 'spatial' with postgis extension

# assumes mapping file in /vagrant/mapping.json
mapping = os.path.abspath('importer' + os.path.sep + 'mapping.json')
print(mapping)

# assumes pbf file in /vagrant/data/
pbf = os.path.abspath('data' + os.path.sep + 'germany-latest.osm.pbf')
print(pbf)

# assumes imposm3 in importer/
imposm_dir = os.path.abspath('importer')
print(imposm_dir)

# Database connection
engine = create_engine('postgresql://' + db_user + ':' + db_pw + '@' + db_host + ':' + str(db_port) + '/' + db_name,
                       echo=True)

# Setup session
metadata = Base.metadata
Session = sessionmaker(bind=engine)
session = Session()


def run():
    # import from pbf file with imposm
    import_from_pbf()

    # osm_admin -> country
    import_from_osm_admin(Country, 2)

    # osm_admin -> state
    import_from_osm_admin(State, 4)

    # osm_admin -> district
    import_from_osm_admin(District, 6)

    # osm_places -> cities
    import_from_osm_places()

    session.commit()
    session.close()


def import_from_pbf():

    connection = 'postgis://' + db_user + ':' + db_pw + '@' + db_host + ':' + str(db_port) + '/' + db_name
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


def import_from_osm_admin(model, admin_level):
    query = session.query(Osm_Admin).filter(Osm_Admin.admin_level == admin_level).all()
    model.__table__.drop(engine, checkfirst=True)
    model.__table__.create(engine)
    for row in query:
        newEntity = model(name=row.name, osm_id=row.osm_id, type=row.type, admin_level=row.admin_level,
                          geometry=func.ST_Transform(row.geometry, 4326))
        session.add(newEntity)


def import_from_osm_places():
    query = session.query(Osm_Places).all()
    Cities.__table__.drop(engine, checkfirst=True)
    Cities.__table__.create(engine)
    for place in query:
        new_city = Cities(name=place.name, osm_id=place.osm_id, type=place.type, z_order=place.z_order,
                          population=place.population, geometry=func.ST_Transform(place.geometry, 4326))
        session.add(new_city)
