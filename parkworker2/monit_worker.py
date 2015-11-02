# coding: utf-8
from parkworker.monit_worker import BaseMonitWorker
from . import settings
from .event import emit_event


class MonitWorker(BaseMonitWorker):
    ZMQ_SERVER_ADDRESS = settings.ZMQ_SERVER_ADDRESS
    ZMQ_MONIT_SCHEDULER_PORT = settings.ZMQ_MONIT_SCHEDULER_PORT

    def emit_event(self, *args, **kwargs):
        return emit_event(*args, **kwargs)


