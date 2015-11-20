# coding: utf-8
from parkworker.worker import BaseWorker
from . import settings
from .event import emit_event


class Worker(BaseWorker):
    ZMQ_SERVER_ADDRESS = settings.ZMQ_SERVER_ADDRESS
    ZMQ_WORKER_REGISTRATOR_PORT = settings.ZMQ_WORKER_REGISTRATOR_PORT

    worker_type = 'python2'

    def emit_event(self, *args, **kwargs):
        return emit_event(*args, **kwargs)


