# coding: utf-8
import re
import os
import tempfile

import ansible.runner
import ansible.inventory

from parkworker.monits.base import Monit, CheckResult
from parkworker import const
from parkworker2 import settings
from swutils.encrypt import decrypt


class ParseStdoutException(Exception):
    pass


class AnsibleMonitMixin(object):

    def run(self, host, remote_user, remote_pass, inventory, kwargs):
        raise NotImplemented()

    def check(self, host, **kwargs):
        remote_user, remote_pass = self._get_user_pass(kwargs)
        inventory = self._create_inventory(host)

        result = self.run(host, remote_user, remote_pass, inventory, kwargs)

        if result['dark'].get(host) and result['dark'][host].get('failed'):
            return CheckResult(
                level=const.LEVEL_FAIL,
                extra=self._correct_result(result),
            )

        return self.process_contacted(result, kwargs)

    def process_contacted(self, result, kwargs):
        level = const.LEVEL_OK
        check_result = CheckResult(
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


class PingMonit(AnsibleMonitMixin, Monit):
    name = 'ansible.ping'
    description = 'Ansible ping host checking.'

    def run(self, host, remote_user, remote_pass, inventory, kwargs):
        runner = ansible.runner.Runner(
            module_name='ping',
            module_args='',
            inventory=inventory,
            pattern=host,
            remote_user=remote_user, remote_pass=remote_pass
        )
        result = runner.run()
        return result


class DiskSpaceMonit(AnsibleMonitMixin, Monit):

    name = 'ansible.disk_space'
    description = 'Ansible disk space host checking. Options: \n' \
                  ' - partitions. Optional. Array with partition names for checking. ' \
                  'For example: ["/", "/var", "/tmp"] \n' \
                  ' - warning_percent. Optional. Default 80. \n' \
                  ' - fail_percent. Optional. Default 95.'

    def run(self, host, remote_user, remote_pass, inventory, kwargs):
        command = 'df -h'
        runner = ansible.runner.Runner(
            module_name='shell',
            module_args=command,
            inventory=inventory,
            pattern=host,
            remote_user=remote_user, remote_pass=remote_pass
        )
        result = runner.run()
        return result

    def process_contacted(self, result, kwargs):
        partitions = kwargs.get('partitions')
        warning_percent = int(kwargs.get('warning_percent', 80))
        fail_percent = int(kwargs.get('fail_percent', 95))

        contacted = self._get_contacted(result)
        stdout = contacted['stdout']
        try:
            space_data = self._parse_space(stdout)
            extra = self._analyze_spaces(space_data, partitions, warning_percent, fail_percent)

            if extra.get('fails'):
                level = const.LEVEL_FAIL
            elif extra.get('warnings'):
                level = const.LEVEL_WARNING
            else:
                level = const.LEVEL_OK

            return CheckResult(
                level=level,
                extra=extra,
            )

        except ParseStdoutException as ex:
            return CheckResult(
                level=const.LEVEL_FAIL,
                extra={
                    'stdout': stdout,
                    'error': 'Parsing stdout error',
                    'description': str(ex),
                }
            )

    @staticmethod
    def _parse_space(stdout):
        space_data = []
        pattern = r'^(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)$'

        for line in stdout.split('\n')[1:]:
            mo = re.match(pattern, line)
            if not mo:
                raise ParseStdoutException('Parsing line "%s" error with pattern "%s"' % (line, pattern))

            groups = mo.groups()
            space_data.append({
                'disk': groups[0],
                'size': groups[1],
                'used': groups[2],
                'used_percent': int(groups[4][:-1]),
                'available': groups[3],
                'partition': groups[5],
            })

        return space_data

    @staticmethod
    def _analyze_spaces(space_data, partitions, warning_percent, fail_percent):
        extra = {'spaces': []}

        for item in space_data:
            if partitions and item['partition'] not in partitions:
                continue

            used_percent = item['used_percent']
            if warning_percent <= used_percent:
                partition_data = {'partition': item['partition'], 'used_percent': used_percent}
                if warning_percent <= used_percent < fail_percent:
                    extra.setdefault('warnings', []).append(partition_data)
                elif fail_percent < used_percent:
                    extra.setdefault('fails', []).append(partition_data)

            extra['spaces'].append(item)

        return extra


