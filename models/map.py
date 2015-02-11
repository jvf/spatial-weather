from webapp import db
from sqlalchemy import Column, Integer, BigInteger, String, Float, \
    ForeignKey, DateTime
from sqlalchemy.orm import relationship, backref
from geoalchemy2 import Geometry, Raster


class Osm_Admin(db.Model):
    __tablename__ = 'osm_admin'
    id = Column(Integer, primary_key=True)
    osm_id = Column(BigInteger)
    name = Column(String)
    type = Column(String)
    admin_level = Column(Integer)
    population = Column(Integer)
    geometry = Column(Geometry(geometry_type='GEOMETRY', srid=4326))

class Country(db.Model):
    __tablename__ = 'country'
    id = Column(Integer, primary_key=True)
    osm_id = Column(BigInteger)
    name = Column(String)
    type = Column(String)
    admin_level = Column(Integer)
    geometry = Column(Geometry(geometry_type='GEOMETRY', srid=4326))


class State(db.Model):
    __tablename__ = 'state'
    id = Column(Integer, primary_key=True)
    osm_id = Column(BigInteger)
    name = Column(String)
    type = Column(String)
    admin_level = Column(Integer)
    geometry = Column(Geometry(geometry_type='GEOMETRY', srid=4326))


class District(db.Model):
    __tablename__ = 'district'
    id = Column(Integer, primary_key=True)
    osm_id = Column(BigInteger)
    name = Column(String)
    type = Column(String)
    admin_level = Column(Integer)
    geometry = Column(Geometry(geometry_type='GEOMETRY', srid=4326))


class Cities(db.Model):
    __tablename__ = 'cities'
    id = Column(Integer, primary_key=True)
    osm_id = Column(BigInteger)
    name = Column(String)
    type = Column(String)
    z_order = Column(Integer)
    population = Column(Integer)
    geometry = Column(Geometry(geometry_type='POINT', srid=4326))


class Station(db.Model):
    __tablename__ = 'stations'
    id = Column(Integer, primary_key=True)
    dwd_id = Column(Integer)
    name = Column(String)
    altitude = Column(Float)
    geometry = Column(Geometry(geometry_type='POINT', srid=4326))
    region = Column(Geometry(geometry_type='GEOMETRY', srid=4326))

    observations = relationship("Observation", backref="station")
    forecasts = relationship("Forecast", backref="station")


''' Alternative zu der kombinierten Station Tabelle:
class Station(Base):
    __tablename__ = 'stations'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    altitude = Column(Float)
    geometry = Column(Geometry(geometry_type='POINT', srid=4326))

    cell = relationship("Cells", backref=backref("station", uselist=False))
    observations = relationship("Observation", backref="station")
    forecasts = relationship("Forecast", backref="station")

class Cells(Base):
    __tablename__ = 'cells'
    id = Column(Integer, primary_key=True)
    geometry = Column(Geometry(geometry_type='GEOMETRY', srid=4326))

    station_id = Column(Integer, ForeignKey('stations.id'))
'''


class ContribState(db.Model):
    __tablename__ = 'contrib_state'
    state_id = Column(Integer, ForeignKey(State.id, ondelete='CASCADE'), primary_key=True)
    station_id = Column(Integer, ForeignKey(Station.id, ondelete='CASCADE' ), primary_key=True)
    area = Column(Float)

    @classmethod
    def fill(cls):
        with db.engine.begin() as c:
            query = """\
TRUNCATE TABLE {tablename};
INSERT INTO {tablename}
SELECT s.id as state_id, st.id as station_id, ST_Area(ST_Intersection(st.region, s.geometry)) as area
  FROM state s, stations st
 WHERE ST_Intersects(s.geometry, st.region);
            """.format(tablename=cls.__tablename__)
            c.execute(query)


class ContribDistrict(db.Model):
    __tablename__ = 'contrib_district'
    district_id = Column(Integer, ForeignKey(District.id, ondelete='CASCADE'), primary_key=True)
    station_id = Column(Integer, ForeignKey(Station.id, ondelete='CASCADE' ), primary_key=True)
    area = Column(Float)

    @classmethod
    def fill(cls):
        with db.engine.begin() as c:
            query = """\
TRUNCATE TABLE {tablename};
INSERT INTO {tablename}
SELECT d.id as district_id, st.id as station_id, ST_Area(ST_Intersection(st.region, d.geometry)) as area
  FROM district d, stations st
 WHERE ST_Intersects(d.geometry, st.region);
            """.format(tablename=cls.__tablename__)
            c.execute(query)


class Observation(db.Model):
    __tablename__ = 'observations'
    id = Column(Integer, primary_key=True)
    date = Column(DateTime)
    temperature = Column(Float)
    rainfall = Column(Float)

    station_id = Column(Integer, ForeignKey('stations.id'))


class Forecast(db.Model):
    __tablename__ = 'forecasts'
    id = Column(Integer, primary_key=True)
    # TODO: Model fields

    station_id = Column(Integer, ForeignKey('stations.id'))


class GFS(db.Model):
    __tablename__ = 'gfs_data'
    forecast_date = Column(DateTime, primary_key=True)
    forecast_hour = Column(Integer, primary_key=True)

    import_id = Column(Integer)

    # Raster should be created on the database level to ensure the srid
    # is correct and stuff
    rast = Column(Raster())


class GFSImport(db.Model):
    __tablename__ = 'gfs_import'
    rid = Column(Integer, primary_key=True)
    filename = Column(String)
    rast = Column(Raster)
