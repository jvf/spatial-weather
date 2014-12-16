#!/usr/bin/env python
from datetime import datetime, timedelta
from urllib.request import urlretrieve
import argparse
import os
import sys
from os import path
import shutil
import time

# .5x.5 grid
URL = 'http://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_hd.pl' \
      '?dir=%2Fgfs.{model_date}{model_hour:02}%2Fmaster' \
      '&file=gfs.t{model_hour:02}z.mastergrb2f{forecast_hour:02}' \
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


def download(url, out, repeat=5, sleep=15):
    run = 0
    while True:
        try: 
            # Be nice and sleep some milli seconds
            time.sleep(sleep)
            
            print("Going to download '{url}' to '{out}'".format(url=url, out=out))
            urlretrieve(url, out)

            return
        except:
            run = run + 1
            if run < repeat:
                print("error in run {} -> retry".format(run))
            else:
                raise


def populate_args(parser):
    parser.add_argument("startdate", type=str, default="latest", nargs="?",
                        help="YYYYMMDDHH")
    parser.add_argument("enddate", type=str, default="latest", nargs="?",
                        help="YYYYMMDDHH")
    parser.add_argument("datadir", type=str,
                        help="Directory where the downloaded files are stored")
    parser.add_argument("--hours_start", type=int, default=0)
    parser.add_argument("--hours_stop", type=int, default=129)
    parser.add_argument("--hours_step", type=int, default=3)

    parser.set_defaults(func=run)

    return parser


def parse_modeldate_arg(datestring):
    if datestring == "latest":
        date = datetime.now().replace(minute=0, second=0, microsecond=0)
        date = date - timedelta(hours=6)
    else:
        date = datetime.strptime(datestring, "%Y%m%d%H")

    # Round to the nearest lower hour that is a multiple of 6.
    date.replace(hour=(date.hour // 6) * 6)

    return date


def run(args):
    startdate = parse_modeldate_arg(args.startdate)
    enddate = parse_modeldate_arg(args.enddate)
    hours = range(args.hours_start, args.hours_stop + 1, args.hours_step)

    while startdate <= enddate:

        outdir = prepare_outputdir(args.datadir, startdate)

        for hour in hours:
            url_ = URL.format(model_date=startdate.strftime("%Y%m%d"),
                              model_hour=startdate.hour,
                              forecast_hour=hour)
            file = "gfs.t{model_hour:02}z.mastergrb2f{forecast_hour:02}".format(
                model_date=startdate.strftime("%Y%m%d"),
                model_hour=startdate.hour,
                forecast_hour=hour
            )

            out = path.join(outdir, file)
            download(url_, out)


        startdate = startdate + timedelta(hours=6)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser = populate_args(parser)
    args = parser.parse_args()
    run(args)
