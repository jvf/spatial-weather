#!/usr/bin/env python
from importer import gfs_download, gfs_import
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    subparsers.required = True
    subparsers.dest = "command"
    download_parser = subparsers.add_parser("download")
    gfs_download.populate_args(download_parser)

    import_parser = subparsers.add_parser("import")
    gfs_import.populate_args(import_parser)

    args = parser.parse_args()
    args.func(args)
