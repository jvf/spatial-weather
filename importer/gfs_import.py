import argparse
import os
from os import path
import re
from datetime import datetime
from subprocess import check_call
from tempfile import TemporaryDirectory

from webapp import db
from models.map import GFS, GFSImport
from .gfs_download import parse_modeldate_arg


def warp(files, tmpdir, srid):
    result = []

    for hour, filename, filepath in files:
        tmpfile = path.join(tmpdir, filename)
        args = ["gdalwarp",
                "-t_srs", "EPSG:{}".format(srid),
                filepath, tmpfile]
        check_call(args)
        result.append((hour, filename, tmpfile))

    return result


def convert2psql(files, tmpdir, srid):
    args = ["raster2pgsql",
            # "-a",  # Append to table
            "-d",    # Drop and recreate
            # "-C",  # Constraints
            "-s", str(srid),  # raster's SRID
            "-F",    # FileName
            ]
    args = args + [f for _, _, f in files]
    args = args + ["public." + GFSImport.__tablename__]

    sqlfile = path.join(tmpdir, "raster.sql")
    with open(sqlfile, "wb") as f:
        check_call(args, stdout=f)

    return sqlfile


def import2db(date, files, sqlfile):
    GFS.__table__.create(db.engine, checkfirst=True)
    GFSImport.__table__.create(db.engine, checkfirst=True)

    # Remove current results for this forecast
    delete = GFS.__table__.delete().where(GFS.forecast_date == date)
    db.engine.execute(delete)

    # Remove old import_ids
    upd = GFS.__table__.update().values(import_id=None)
    db.engine.execute(upd)

    # Import the generated raster to the import table
    with open(sqlfile, "r") as f:
        for line in f:
            db.engine.execute(line)

    for (hour, filename, _) in files:
        import_id = db.session.query(GFSImport.rid)\
            .filter(GFSImport.filename == filename).scalar()

        g = GFS(forecast_date=date, forecast_hour=hour, import_id=import_id)
        db.session.add(g)

    db.session.commit()

    stmt = db.session.query(GFSImport.rast)\
        .filter(GFSImport.rid == GFS.import_id).limit(1).statement

    upd = GFS.__table__.update() \
        .where(GFS.import_id != None) \
        .values(rast=stmt, import_id=None)
    db.engine.execute(upd)


def populate_args(parser):
    parser.add_argument("datadir",
                        help="Directory where the downloaded files are stored")
    parser.add_argument("startdate", type=str, default="latest", nargs="?",
                        help="YYYYMMDDHH")
    parser.add_argument("enddate", type=str, default="latest", nargs="?",
                        help="YYYYMMDDHH")
    parser.set_defaults(func=run)

    return parser


def parse_dirs(datadir, startdate, enddate):
    dirs = []
    for name in os.listdir(datadir):
        dirpath = path.join(datadir, name)
        if not path.isdir(dirpath):
            continue

        try:
            date = datetime.strptime(name, "%Y%m%d%H")
        except ValueError:
            continue

        if startdate <= date <= enddate:
            dirs.append((date, dirpath))

    return sorted(dirs)


def parse_files(dirdate, dirpath, hours):
    files = []
    pattern = re.compile("gfs.t{:02}z.mastergrb2f(\d+)".format(dirdate.hour))

    for name in os.listdir(dirpath):
        filepath = path.join(dirpath, name)
        if not path.isfile(filepath):
            continue

        m = pattern.match(name)
        if not m:
            continue

        hour = int(m.group(1))
        if hour not in hours:
            continue

        files.append((hour, name, filepath))

    return sorted(files)


def run(args):
    startdate = parse_modeldate_arg(args.startdate)
    enddate = parse_modeldate_arg(args.enddate)

    hours = range(0, 129 + 1, 3)

    assert path.isdir(args.datadir), "[datadir] has to be a directory"
    dirs = parse_dirs(args.datadir, startdate, enddate)

    for date, dir in dirs:
        files = parse_files(date, dir, hours)

        with TemporaryDirectory() as tmpdir:
            warped = warp(files, tmpdir, 4326)
            sqlfile = convert2psql(warped, tmpdir, 4326)
            import2db(date, warped, sqlfile)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser = populate_args(parser)
    args = parser.parse_args()
    run(args)