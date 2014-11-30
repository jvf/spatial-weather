from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, BigInteger, String
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