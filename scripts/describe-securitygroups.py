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

from pprint import pprint
import argparse
import boto
import boto.ec2

# configure command line argument parsing
parser = argparse.ArgumentParser(description='Describe EC2 security groups in all/some available EC2 regions')
parser.add_argument("-f", "--filter", action="append", help="A (key,value) pair for a filter to limit the results returned. [can be used multiple times]")
parser.add_argument("-li", "--instances", action="store_true", help="List all instances currently running within this security group")
parser.add_argument("-lr", "--rules", action="store_true", help="List all rules currently active in this security group")
parser.add_argument("-r", "--region", help="A region substring selector (e.g. 'us-west')")
parser.add_argument("--access_key_id", dest='aws_access_key_id', help="Your AWS Access Key ID")
parser.add_argument("--secret_access_key", dest='aws_secret_access_key', help="Your AWS Secret Access Key")
args = parser.parse_args()

credentials = {'aws_access_key_id': args.aws_access_key_id, 'aws_secret_access_key': args.aws_secret_access_key}

def isSelected(region):
    return True if region.name.find(args.region) != -1 else False

# execute business logic
heading = "Describing EC2 security groups"
regions = boto.ec2.regions()
if args.region:
    heading += " (filtered by region '" + args.region + "')"
    regions = filter(isSelected, regions)
if args.filter:
    for filter in args.filter:
        heading += " (filtered by filter '" + filter + "')"

filters = dict([filter.split('=') for filter in args.filter]) if args.filter else None

print heading + ":"
for region in regions:
    pprint(region.name, indent=2)
    try:
        ec2 = boto.connect_ec2(region=region, **credentials)
        groups = ec2.get_all_security_groups(filters=filters)
        for group in groups:
            vpc_id = "|" + group.vpc_id if group.vpc_id else ""
            print("\n" + group.name + " (" + group.id + vpc_id + " - " + group.description + "):")
            if args.rules:
                print("... rules ...")
                for rule in group.rules:
                    pprint(rule)
                if group.vpc_id:
                    print("... rules (egress) ...")
                    for rule in group.rules_egress:
                        pprint(rule)
            if args.instances:
                print("... instances ...")
                for instance in group.instances():
                    pprint(instance)
    except boto.exception.BotoServerError, e:
        print e.error_message
