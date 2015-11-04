# coding: utf-8
import os
import tempfile

import ansible.runner
import ansible.inventory

from parkworker.monits.base import Monit, CheckResult
from parkworker import const
from parkworker2 import settings
from swutils.encrypt import decrypt


class AnsibleMonitMixin(object):
    @staticmethod
    def _create_inventory(host):
        fd, host_list_path = tempfile.mkstemp()
        host_list_file = os.fdopen(fd, 'w')
        host_list_file.write(host)
        host_list_file.close()

        inventory = ansible.inventory.Inventory(host_list_path)
        return inventory

    @staticmethod
    def _get_user_pass(kwargs):
        remote_user = kwargs['credentials']['ssh']['username']
        remote_encrypted_pass = kwargs['credentials']['ssh']['encrypted_password']
        remote_pass = decrypt(remote_encrypted_pass, settings.SECRET_KEY.encode('utf-8'))
        return remote_user, remote_pass

    @classmethod
    def _correct_result(cls, result):
        corrected_result = {}
        for k, v in result.iteritems():
            if isinstance(v, dict):
                v = cls._correct_result(v)
            # mongo reserved symbols "." and "$"
            k = k.replace('.', '-')
            k = k.replace('$', 'S')
            corrected_result[k] = v
        return corrected_result


class PingMonit(AnsibleMonitMixin, Monit):
    name = 'ansible.ping'
    description = 'Ansible ping host checking.'

    def check(self, host, **kwargs):
        remote_user, remote_pass = self._get_user_pass(kwargs)
        inventory = self._create_inventory(host)

        runner = ansible.runner.Runner(
            module_name='ping',
            module_args='',
            inventory=inventory,
            pattern=host,
            remote_user=remote_user, remote_pass=remote_pass
        )
        result = runner.run()

        if result['dark'].get(host) and result['dark'][host].get('failed'):
            level = const.LEVEL_FAIL
        else:
            level = const.LEVEL_OK

        check_result = CheckResult(
            level=level,
            extra=self._correct_result(result),
        )
        return check_result


