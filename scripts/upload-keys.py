#!/usr/bin/env python
# Copyright (c) 2012 Steffen Opel http://opelbrothers.net/
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

from boto.s3.connection import Location
from boto.s3.key import Key
from botocross.s3 import RegionMap, class_iterator
from pprint import pprint
import argparse
import boto
import boto.s3
import botocross as bc
import logging
import os

# configure command line argument parsing
parser = argparse.ArgumentParser(description='Upload a file to a S3 bucket in all/some available S3 regions',
                                 parents=[bc.build_region_parser(), bc.build_common_parser()])
parser.add_argument("bucket", help="A bucket name (will get region suffix)")
parser.add_argument("file", help="A local file (e.g. ./test.txt)")
args = parser.parse_args()

# process common command line arguments
log = logging.getLogger('botocross')
bc.configure_logging(log, args.log_level)
credentials = bc.parse_credentials(args)
locations = bc.filter_regions_s3(class_iterator(Location), args.region)

# execute business logic
log.info("Uploading to S3 buckets named '" + args.bucket + "':")

file = open(args.file, 'r')
filePath, fileName = os.path.split(file.name)
log.debug(filePath)
log.debug(fileName)

s3 = boto.connect_s3(**credentials)

for location in locations:
    region = RegionMap[location]
    pprint(region, indent=2)
    try:
        bucket_name = args.bucket + '-' + region
        bucket = s3.get_bucket(bucket_name)
        key = Key(bucket)
        key.name = fileName
        print 'Uploading to bucket ' + bucket_name
        key.set_contents_from_filename(args.file)
    except boto.exception.BotoServerError, e:
        log.error(e.error_message)
