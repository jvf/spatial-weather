import os
import subprocess
from sqlalchemy import func
from webapp import app, db
from models.map import Osm_Admin, Country, State, District, Cities


# assumes an existing db 'spatial' with postgis extension

# assumes mapping file in /vagrant/mapping.json
mapping = os.path.abspath('importer' + os.path.sep + 'mapping.json')

# assumes pbf file in /vagrant/data/
pbf = os.path.abspath('data' + os.path.sep + 'germany-latest.osm.pbf')

# assumes imposm3 in importer/
imposm_dir = os.path.abspath('importer')


def run(imposm, simplify, load, drop_tables):

    # import from pbf file with imposm
    if imposm:
        import_from_pbf()

    if simplify:
        db.session.execute("""\
-- Delete all unneeded admin levels
DELETE FROM osm_admin
  WHERE admin_level != 2 AND
    admin_level != 4 AND
    admin_level != 6 AND
    admin_level != 9
;

-- Delete all unneeded rows with admin level 9 (keep only rows of admin level 9 contained in the states hamburg and berlin)
WITH
berlin AS
(
    SELECT geometry
    FROM osm_admin
    WHERE admin_level = 4 AND name = 'Berlin'
),
hamburg AS
(
    SELECT geometry
    FROM osm_admin
    WHERE admin_level = 4 AND name = 'Hamburg'
),
quarter AS
(
    SELECT a.id, a.osm_id, a.name, a.type, a.admin_level, a.population, a.geometry
    FROM osm_admin a, berlin b, hamburg h
    WHERE a.admin_level = 9 AND ST_Contains(ST_Union(b.geometry, h.geometry), a.geometry)
)

DELETE FROM osm_admin
WHERE admin_level = 9 AND id NOT IN (SELECT id FROM quarter);

-- Change Projection
ALTER TABLE osm_admin ALTER COLUMN geometry TYPE geometry(Geometry);
UPDATE osm_admin SET geometry = ST_Transform(geometry, 4326);
ALTER TABLE osm_admin ALTER COLUMN geometry TYPE geometry(Geometry, 4326);

-- Install SimplifyEdgeGeom function
CREATE OR REPLACE FUNCTION SimplifyEdgeGeom(atopo varchar, anedge int, maxtolerance float8)
RETURNS float8 AS $$
DECLARE
  tol float8;
  sql varchar;
BEGIN
  tol := maxtolerance;
  LOOP
    sql := 'SELECT topology.ST_ChangeEdgeGeom(' || quote_literal(atopo) || ', ' || anedge
      || ', ST_Simplify(geom, ' || tol || ')) FROM '
      || quote_ident(atopo) || '.edge WHERE edge_id = ' || anedge;
    BEGIN
      RAISE DEBUG 'Running %', sql;
      EXECUTE sql;
      RETURN tol;
    EXCEPTION
     WHEN OTHERS THEN
      RAISE WARNING 'Simplification of edge % with tolerance % failed: %', anedge, tol, SQLERRM;
      tol := round( (tol/2.0) * 1e8 ) / 1e8; -- round to get to zero quicker
      IF tol = 0 THEN RAISE EXCEPTION '%', SQLERRM; END IF;
    END;
  END LOOP;
END
$$ LANGUAGE 'plpgsql' STABLE STRICT;

-- Create a topology
SELECT topology.CreateTopology('osm_admin_topo', find_srid('public', 'osm_admin', 'geometry'));

-- Add a layer
SELECT AddTopoGeometryColumn('osm_admin_topo', 'public', 'osm_admin', 'topogeom', 'MULTIPOLYGON');

-- Populate the layer and the topology
UPDATE osm_admin SET topogeom = toTopoGeom(geometry, 'osm_admin_topo', 1);

-- Simplify all edges up to 0.01 units
SELECT SimplifyEdgeGeom('osm_admin_topo', edge_id, 0.01) FROM osm_admin_topo.edge;

-- Convert the TopoGeometries to Geometries for visualization
ALTER TABLE osm_admin ADD geomfull Geometry(Geometry, 4326);

UPDATE osm_admin
   SET geomfull = geometry,
       geometry = topogeom::geometry;""")


    if load:
        # osm_admin -> country
        create_from_admin(Country, 2)

        # osm_admin -> state
        create_from_admin(State, 4)

        # osm_admin -> district
        create_from_admin(District, 6)

        db.session.commit()

    # drop the imposm tables
    if drop_tables:
        Osm_Admin.__table__.drop(db.engine, checkfirst=True)


def import_from_pbf():

    connection = 'postgis://' + app.config['DB_USER'] + ':' + app.config['DB_PW'] + '@' + app.config['DB_HOST'] + ':' \
                 + str(app.config['DB_PORT']) + '/' + app.config['DB_NAME']
    os.environ["PATH"] += ":" + imposm_dir
    print(os.environ["PATH"])
    try:
        cmd = " ".join(['import', '-overwritecache', '-connection', connection, '-mapping', mapping, '-read', pbf, '-write'])
        subprocess.check_call(['imposm3', cmd])
        cmd = " ".join(['import', '-connection', connection, '-mapping', mapping, '-deployproduction'])
        subprocess.check_call(['imposm3', cmd])
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
                                 geometry=row.geometry))
