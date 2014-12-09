from datetime import datetime, timedelta
from urllib.request import urlretrieve
import argparse
import os
from os import path
import shutil
import time

# .5x.5 grid
URL = 'http://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_hd.pl' \
      '?dir=%2Fgfs.{model_date}{model_hour:02}%2Fmaster' \
      '&file=gfs.t{model_hour}z.mastergrb2f{forecast_hour:02}' \
      '&lev_2_m_above_ground=on' \
      '&lev_entire_atmosphere_%5C%28considered_as_a_single_layer%5C%29=on' \
      '&var_PWAT=on' \
      '&var_TMAX=on' \
      '&var_TMIN=on' \
      '&var_TMP=on' \
      '&subregion=' \
        '&leftlon=5' \
        '&rightlon=16' \
        '&toplat=56' \
        '&bottomlat=46'


def prepare_outputdir(output, modeldate, keep=False):

    outdir = path.join(output, modeldate.strftime("%Y%m%d%H"))

    assert not path.exists(outdir) or path.isdir(outdir)
    if path.isdir(outdir):
        if keep:
            raise Exception("outdir exists")
        else:
            shutil.rmtree(outdir)

    os.mkdir(outdir)
    return outdir


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("modeldate", type=str, default="latest")
    parser.add_argument("--download-range", type=str, default=None)
    parser.add_argument("output", type=str)
    parser.add_argument("--hours_start", type=int, default=0)
    parser.add_argument("--hours_stop", type=int, default=129)
    parser.add_argument("--hours_step", type=int, default=3)
    args = parser.parse_args()

    if args.modeldate == "latest":
        modeldate = datetime.now().replace(minute=0, second=0, microsecond=0)
        modeldate = modeldate - timedelta(hours=6)
    else:
        modeldate = datetime.strptime(args.modeldate, "%Y%m%d%H")
    modeldate = modeldate.replace(hour=(modeldate.hour // 6) * 6)

    hours = range(args.hours_start, args.hours_stop + 1, args.hours_step)
    if args.download_range:
        enddate = datetime.strptime(args.download_range, "%Y%m%d%H")
        enddate = enddate.replace(hour=(enddate.hour // 6) * 6)
    else:
        enddate = modeldate

    while modeldate <= enddate:

        outdir = prepare_outputdir(args.output, modeldate)

        for hour in hours:
            url_ = URL.format(model_date=modeldate.strftime("%Y%m%d"),
                              model_hour=modeldate.hour,
                              forecast_hour=hour)
            file = "gfs.t{model_hour}z.mastergrb2f{forecast_hour:02}".format(
                model_date=modeldate.strftime("%Y%m%d"),
                model_hour=modeldate.hour,
                forecast_hour=hour
            )

            out = path.join(outdir, file)
            print("Going to download '{url}' to '{out}'".format(url=url_, out=out))
            urlretrieve(url_, out)

            # Be nice and sleep some milli seconds
            time.sleep(0.01)

        modeldate = modeldate + timedelta(hours=6)


if __name__ == '__main__':
    main()
