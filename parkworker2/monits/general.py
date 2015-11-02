# coding: utf-8
import subprocess

from parkworker.monits.base import Monit, CheckResult


class PingMonit(Monit):
    name = 'general.ping'
    description = 'Ping host checking.'

    def check(self, host, **kwargs):
        return_code = subprocess.call(
            ['ping', host, '-c1'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        is_success = return_code == 0

        check_result = CheckResult(
            is_success=is_success,
            extra={},
        )
        return check_result
