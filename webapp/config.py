__author__ = 'jvf'

# connection
DB_USER = 'myapp'
DB_PW = 'dbpass'
DB_HOST = 'localhost'
DB_PORT = 15432
DB_NAME = 'spatial'  # assumes an existing db 'spatial' with postgis extension
JSONIFY_PRETTYPRINT_REGULAR = False
JSON_SORT_KEYS = False

SQLALCHEMY_DATABASE_URI = 'postgresql://' + DB_USER + ':' + DB_PW + '@' + DB_HOST + ':' + str(DB_PORT) + '/' + DB_NAME
