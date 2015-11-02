#!/usr/bin/env python2
# coding: utf-8

from parkworker.monits.base import Monit
import argparse

parser = argparse.ArgumentParser(description='Run monitoring checks manually.')
parser.add_argument('monit_name', type=str, help='Monitoring name. For example: general.ping')
parser.add_argument('hosts', nargs='+', type=str, help='Hosts for monitoring')
args = parser.parse_args()


monit = Monit.get_monit(args.monit_name)()
for host in args.hosts:
    result = monit.check(host)
    print(monit.name, host, ':', result.is_success)
