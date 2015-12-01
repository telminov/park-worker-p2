# coding: utf-8
import tempfile
import os

import ansible.inventory
from parkworker import const
from parkworker.task_processor import TaskResult
from parkworker2 import settings
from swutils.encrypt import decrypt


class AnsibleMixin(object):

    def run(self, host, remote_user, remote_pass, inventory, kwargs):
        raise NotImplemented()

    def check(self, host, **kwargs):
        remote_user, remote_pass = self._get_user_pass(kwargs)
        inventory = self._create_inventory(host)

        result = self.run(host, remote_user, remote_pass, inventory, kwargs)

        if result['dark'].get(host) and result['dark'][host].get('failed'):
            return TaskResult(
                level=const.LEVEL_FAIL,
                extra=self._correct_result(result),
            )

        return self.process_contacted(result, kwargs)

    def work(self, host, **kwargs):
        return self.check(host, **kwargs)

    def process_contacted(self, result, kwargs):
        level = const.LEVEL_OK
        check_result = TaskResult(
            level=level,
            extra=self._correct_result(result),
        )
        return check_result

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

    @staticmethod
    def _get_contacted(result):
        return result['contacted'].values()[0]
