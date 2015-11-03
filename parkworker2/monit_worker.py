# coding: utf-8
from parkworker.monit_worker import BaseMonitWorker
from . import settings
from .event import emit_event


class MonitWorker(BaseMonitWorker):
    ZMQ_SERVER_ADDRESS = settings.ZMQ_SERVER_ADDRESS
    ZMQ_WORKER_REGISTRATOR_PORT = settings.ZMQ_WORKER_REGISTRATOR_PORT

    worker_type = 'python2'

    def emit_event(self, *args, **kwargs):
        return emit_event(*args, **kwargs)


