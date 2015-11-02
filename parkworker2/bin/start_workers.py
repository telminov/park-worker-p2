#!/usr/bin/env python2
# coding: utf-8
from parkworker2.monit_worker import MonitWorker
import argparse

parser = argparse.ArgumentParser(description='Start monitoring workers.')
parser.add_argument('workers_count', type=int, help='Number of workers.', default=2, nargs='?')
args = parser.parse_args()

workers = []
for i in range(0, args.workers_count):
    worker_id = i + 1
    worker = MonitWorker()
    worker.setup(worker_id)
    worker.start()
    workers.append(worker)

for worker in workers:
    worker.join()

