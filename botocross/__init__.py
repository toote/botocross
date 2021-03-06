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

import argparse
import logging
import re
botocross_log = logging.getLogger('botocross')

def configure_logger(logger, level):
    logger.setLevel(level)

    # configure default stdout handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logger.getEffectiveLevel())
    logger.addHandler(console_handler)

def configure_logging(logger, level):
    # convert level string to format suitable for logging package
    level = getattr(logging, level.upper())

    # configure default stdout handlers for botocross and upstream boto
    configure_logger(logger, level)
    boto_logger = logging.getLogger('boto')
    configure_logger(boto_logger, level)

def create_arn(iam, service, region, resource):
    from botocross.iam.accountinfo import AccountInfo
    accountInfo = AccountInfo(iam)
    account = accountInfo.describe()
    return 'arn:aws:' + service + ':' + region + ':' + account.id + ':' + resource

# REVIEW: refactor to argparse custom action for inline usage?!
def build_filter(filter_args, exclude_args):
    return {'filters': build_filter_params(filter_args), 'excludes': build_filter_params(exclude_args)}

def build_filter_params(filter_args):
    from collections import defaultdict

    if not filter_args:
        return None

    params = defaultdict(list)
    filters = [filter_arg.split('=') for filter_arg in filter_args]
    for k, v in filters:
        params[k].append(v)
    botocross_log.info(filter_args)
    botocross_log.debug(params)
    return params

def build_common_parser():
    from botocross import __version__
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-v", "--verbose", action='store_true')  # REVIEW: drop in favor of a log formatter?!
    parser.add_argument("--access_key_id", dest='aws_access_key_id', help="Your AWS Access Key ID")
    parser.add_argument("--secret_access_key", dest='aws_secret_access_key', help="Your AWS Secret Access Key")
    parser.add_argument("-l", "--log", dest='log_level', default='WARNING',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help="The logging level to use. [default: WARNING]")
    parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    return parser

def build_region_parser():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-r", "--region", default="(ap|eu|sa|us)-[enws]",
                                      help="A regular expression based region substring selector [default '(ap|eu|sa|us)-[enws]']")
    return parser

def build_filter_parser(resource_name, add_ids=True):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-f", "--filter", action="append",
                                      help="A {0} filter. [can be used multiple times]".format(resource_name))
    parser.add_argument("-x", "--exclude", action="append",
                                      help="A {0} filter (matching ones are excluded). [can be used multiple times]"
                                      .format(resource_name))
    if add_ids:
        parser.add_argument("-i", "--id", dest="resource_ids", action="append",
                                          help="A {0} id. [can be used multiple times]".format(resource_name))
    return parser

def build_backup_parser(resource_name, expire_only=False, backup_retention=None):
    parser = argparse.ArgumentParser(add_help=False)
    if not expire_only:
        parser.add_argument("-d", "--description",
                            help="A description for the {0} [default: <provided>]".format(resource_name))
    default_retention_help = str(backup_retention) if backup_retention else "None, i.e. don't expire"
    parser.add_argument("-br", "--backup_retention", type=int, default=backup_retention,
                        help="The number of backups to retain (correlated via backup_set). [default: {0}]".format(default_retention_help))
    parser.add_argument("-bs", "--backup_set", default='default',
                        help="A backup set name (determines retention correlation). [default: 'default']")
    if not expire_only:
        parser.add_argument("-bt", "--backup_timeout", default=None,
                            help="Maximum duration to await successful resource creation - an ISO 8601 duration, e.g. 'PT8H' (8 hours). [default: None, i.e. don't await]")
    parser.add_argument("-ns", "--no_origin_safeguard", action="store_true",
                        help="Allow deletion of images originating from other tools. [default: False]")
    return parser

def parse_credentials(args):
    return {'aws_access_key_id': args.aws_access_key_id, 'aws_secret_access_key': args.aws_secret_access_key}

def filter_list_by_attribute(includes, excludes, attribute):
    excluded_ids = set([getattr(exclude, attribute) for exclude in excludes])
    return [include for include in includes if getattr(include, attribute) not in excluded_ids]

def is_region_selected(region, name):
    pattern = re.compile(name, re.IGNORECASE)
    return True if re.search(pattern, region.name) != None else False

def filter_regions(regions, region):
    if region:
        botocross_log.info("... (filtered by region '" + region + "')")
        regions = filter(lambda x: is_region_selected(x, region), regions)
    return regions

# REVIEW: remove this S3 legacy induced partial duplication, if possible.
def is_region_selected_s3(region, name):
    from botocross.s3 import RegionMap
    pattern = re.compile(name, re.IGNORECASE)
    return True if re.search(pattern, RegionMap[region]) != None else False

# REVIEW: remove this S3 legacy induced partial duplication, if possible.
def filter_regions_s3(regions, region):
    if region:
        botocross_log.info("... (filtered by S3 region '" + region + "')")
        regions = filter(lambda x: is_region_selected_s3(x, region), regions)
    return regions

# pylint: disable=R0903
class ExitCodes:
    (OK, FAIL) = range(0, 2)

class BotocrossAwaitTimeoutError(StandardError):
    """
    Timeout error when awaiting a resource transition.
    """
    def __init__(self, message):
        Exception.__init__(self, message)

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
