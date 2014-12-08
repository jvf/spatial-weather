import argparse
import os
from os import path
import shutil
from datetime import datetime
from subprocess import check_call, check_output
from webapp import db
from models.map import GFS, GFSImport


def prepare_outputdir(outdir, keep=False):
    assert not path.exists(outdir) or path.isdir(outdir)

    if path.isdir(outdir):
        if keep:
            raise Exception("outdir exists")
        else:
            shutil.rmtree(outdir)

    os.mkdir(outdir)


def download_gfs(forecast, variables, level, hours, output):
    # TODO: reimplement in python and don't use curl
    args = ["perl", "get_gfs.pl","data",
            forecast.strftime("%Y%m%d%H"),
            str(hours.start), str(hours.stop - 1), str(hours.step),
            ":".join(variables), ":".join(level),
            output]
    check_call(args)

    result = []
    for hour in hours:
        filename = "gfs.t{HH:02}z.pgrb2f{FHR:02}".format(HH=forecast.hour,
                                                         FHR=hour)
        assert path.exists(path.join(output, filename))

        result.append((hour, filename))

    return result


def warp(files, srid, outdir):
    result = []

    for (hour, src_file) in files:
        filename = "gfs-{:02}-{}.grib2".format(hour, srid)

        args = ["gdalwarp",
                "-t_srs", "EPSG:{}".format(srid),
                path.join(outdir, src_file),
                path.join(outdir, filename)]
        check_call(args)

        result.append((hour, filename))

    return result


def convert2psql(files, srid, outdir):
    args = ["raster2pgsql",
            # "-a",  # Append to table
            "-d",    # Drop and recreate
            # "-C",  # Constraints
            "-s", str(srid),  # raster's SRID
            "-F",    # FileName
            ]
    args = args + [path.join(outdir, file) for _, file in files]
    args = args + ["public." + GFSImport.__tablename__]

    sqlfile = "raster.sql"
    with open(path.join(outdir, sqlfile), "wb") as f:
        check_call(args, stdout=f)

    return sqlfile


def import2db(forecast, files, sqlfile, outdir):
    # Remove current results for this forecast
    delete = GFS.__table__.delete().where(GFS.forecast_date == forecast)
    db.engine.execute(delete)

    # Remove old import_ids
    upd = GFS.__table__.update().values(import_id=None)
    db.engine.execute(upd)

    # Import the generated raster to the import table
    with open(path.join(outdir, sqlfile), "r") as f:
        for line in f:
            db.engine.execute(line)

    for (hour, filename) in files:
        import_id = db.session.query(GFSImport.rid)\
            .filter(GFSImport.filename == filename).scalar()

        g = GFS(forecast_date=forecast, forecast_hour=hour, import_id=import_id)
        db.session.add(g)

    db.session.commit()

    stmt = db.session.query(GFSImport.rast)\
        .filter(GFSImport.rid == GFS.import_id).limit(1).statement

    upd = GFS.__table__.update() \
        .where(GFS.import_id is not None) \
        .values(rast=stmt, import_id=None)
    db.engine.execute(upd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep-existing", action='store_true')
    parser.add_argument("forecast", type=str, default="now")
    parser.add_argument("hours_start", type=int)
    parser.add_argument("hours_stop", type=int)
    parser.add_argument("hours_step", type=int)
    parser.add_argument("variables", type=lambda s: s.split(":"))
    parser.add_argument("level", type=lambda s: s.split(":"))
    parser.add_argument("output", type=str)

    args = parser.parse_args()
    print(args)

    if args.forecast == "now":
        forecast = datetime.now().replace(minute=0, second=0, microsecond=0)
        forecast = forecast.replace(hour=forecast.hour - 6)
    else:
        forecast = datetime.strptime(args.forecast, "%Y%m%d%H")
    forecast = forecast.replace(hour=(forecast.hour // 6) * 6)

    outdir = path.join(args.output, forecast.strftime("%Y%m%d%H"))
    prepare_outputdir(outdir, args.keep_existing)

    hours = range(args.hours_start, args.hours_stop + 1, args.hours_step)

    files = download_gfs(forecast, args.variables, args.level, hours, outdir)
    print(files)
    files = warp(files, 4326, outdir)
    print(files)

    sqlfile = convert2psql(files, 4326, outdir)
    import2db(forecast, files, sqlfile, outdir)




if __name__ == "__main__":
    main()