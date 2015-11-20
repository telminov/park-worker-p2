#!/usr/bin/env python2
# coding: utf-8
from time import sleep

from parkworker2.worker import Worker
import argparse

parser = argparse.ArgumentParser(description='Start monitoring workers.')
parser.add_argument('workers_count', type=int, help='Number of workers.', default=2, nargs='?')
args = parser.parse_args()

workers = []
for i in range(0, args.workers_count):
    worker_id = i + 1
    worker = Worker()
    worker.setup(worker_id)
    worker.start()
    workers.append(worker)

try:
    while True:
        sleep(1)
finally:
    for worker in workers:
        worker.stop()
    for worker in workers:
        worker.join()

