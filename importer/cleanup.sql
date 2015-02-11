--delete schemas and entries from simplification

DROP SCHEMA IF EXISTS osm_admin_topo CASCADE;

DELETE FROM topology.layer
WHERE table_name = 'osm_admin';

DELETE FROM topology.topology
WHERE name = 'osm_admin_topo';