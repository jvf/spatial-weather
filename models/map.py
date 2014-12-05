from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, BigInteger, String, Float, \
    ForeignKey, DateTime
from sqlalchemy.orm import relationship, backref
from geoalchemy2 import Geometry

Base = declarative_base()


class Osm_Admin(Base):
    __tablename__ = 'osm_admin'
    id = Column(Integer, primary_key=True)
    osm_id = Column(BigInteger)
    name = Column(String)
    type = Column(String)
    admin_level = Column(Integer)
    population = Column(Integer)
    geometry = Column(Geometry(geometry_type='GEOMETRY', srid=3857))


class Osm_Places(Base):
    __tablename__ = 'osm_places'
    id = Column(Integer, primary_key=True)
    osm_id = Column(BigInteger)
    name = Column(String)
    type = Column(String)
    z_order = Column(Integer)
    population = Column(Integer)
    geometry = Column(Geometry(geometry_type='POINT', srid=3857))


class Country(Base):
    __tablename__ = 'country'
    id = Column(Integer, primary_key=True)
    osm_id = Column(BigInteger)
    name = Column(String)
    type = Column(String)
    admin_level = Column(Integer)
    geometry = Column(Geometry(geometry_type='GEOMETRY', srid=4326))


class State(Base):
    __tablename__ = 'state'
    id = Column(Integer, primary_key=True)
    osm_id = Column(BigInteger)
    name = Column(String)
    type = Column(String)
    admin_level = Column(Integer)
    geometry = Column(Geometry(geometry_type='GEOMETRY', srid=4326))


class District(Base):
    __tablename__ = 'district'
    id = Column(Integer, primary_key=True)
    osm_id = Column(BigInteger)
    name = Column(String)
    type = Column(String)
    admin_level = Column(Integer)
    geometry = Column(Geometry(geometry_type='GEOMETRY', srid=4326))


class Cities(Base):
    __tablename__ = 'cities'
    id = Column(Integer, primary_key=True)
    osm_id = Column(BigInteger)
    name = Column(String)
    type = Column(String)
    z_order = Column(Integer)
    population = Column(Integer)
    geometry = Column(Geometry(geometry_type='POINT', srid=4326))


class Station(Base):
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


class Observation(Base):
    __tablename__ = 'observations'
    id = Column(Integer, primary_key=True)
    date = Column(DateTime)
    temperature = Column(Float)
    rainfall = Column(Float)

    station_id = Column(Integer, ForeignKey('stations.id'))


class Forecast(Base):
    __tablename__ = 'forecasts'
    id = Column(Integer, primary_key=True)
    # TODO: Model fields

    station_id = Column(Integer, ForeignKey('stations.id'))
