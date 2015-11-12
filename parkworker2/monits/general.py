# coding: utf-8
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


class HostFactsMonit(AnsibleMonitMixin, Monit):
    name = 'ansible.host_facts'
    description = 'Get host facts. Monit may be useful for inheritance.'

    def run(self, host, remote_user, remote_pass, inventory, kwargs):
        runner = ansible.runner.Runner(
            module_name='setup',
            module_args='',
            inventory=inventory,
            pattern=host,
            remote_user=remote_user, remote_pass=remote_pass
        )
        result = runner.run()
        return result

    def process_contacted(self, result, kwargs):
        """
        method for override process data logic
        """
        contacted = self._get_contacted(result)
        host_data = self.get_host_data(contacted)
        return CheckResult(
            level=const.LEVEL_OK,
            extra=host_data,
        )

    @staticmethod
    def get_host_data(contacted):
        devices = {}
        for name, data in contacted['ansible_facts']['ansible_devices'].items():
            partitions = []
            for partition_name, partition_data in data['partitions'].items():
                partitions.append({
                    'name': partition_name,
                    'size': partition_data['size'],
                })

            devices[name] = {
                'model': data['model'],
                'size': data['size'],
                'vendor': data['vendor'],
                'removable': data['removable'],
                'partitions': partitions,
            }

        docker = None
        if 'ansible_docker0' in contacted['ansible_facts']:
            docker = {
                'active': contacted['ansible_facts']['ansible_docker0']['active'],
                'ipv4': contacted['ansible_facts']['ansible_docker0']['ipv4'],
            }

        return {
            'name': contacted['ansible_facts']['ansible_product_name'],
            'hostname': contacted['ansible_facts']['ansible_hostname'],
            'os': {
                'family': contacted['ansible_facts']['ansible_os_family'],
                'kernel': contacted['ansible_facts']['ansible_kernel'],
                'distribution': {
                    'name': contacted['ansible_facts']['ansible_distribution'],
                    'version': contacted['ansible_facts']['ansible_distribution_version'],
                    'release': contacted['ansible_facts']['ansible_distribution_release'],
                },
                'architecture': contacted['ansible_facts']['ansible_architecture'],
            },
            'processors': contacted['ansible_facts']['ansible_processor'],
            'memory': {
                'free': contacted['ansible_facts']['ansible_memfree_mb'],
                'total': contacted['ansible_facts']['ansible_memtotal_mb'],
            },
            'swap': {
                'free': int(contacted['ansible_facts'].get('ansible_swapfree_mb', 0)),
                'total': int(contacted['ansible_facts'].get('ansible_swaptotal_mb', 0)),
            },
            'network': {
                'ipv4': {
                    'default': contacted['ansible_facts']['ansible_default_ipv4'],
                    'all': contacted['ansible_facts']['ansible_all_ipv4_addresses'],
                },
                'ipv6': {
                    'default': contacted['ansible_facts']['ansible_default_ipv6'],
                    'all': contacted['ansible_facts']['ansible_all_ipv6_addresses'],
                }
            },
            'devices': devices,
            'mounts': contacted['ansible_facts']['ansible_mounts'],
            'interfaces': contacted['ansible_facts']['ansible_interfaces'],
            'docker': docker,
            'env': contacted['ansible_facts']['ansible_env'],
            'date_time': contacted['ansible_facts']['ansible_date_time'],
        }


class SwapMonit(HostFactsMonit):

    name = 'ansible.swap'
    description = 'Ansible swap host checking. Options: \n' \
                  ' - warning. Optional. Percents. Default 50. \n' \
                  ' - fail. Optional. Percents. Default 90.'

    def process_contacted(self, result, kwargs):
        warning_percent = int(kwargs.get('warning', 50))
        fail_percent = int(kwargs.get('fail', 90))

        contacted = self._get_contacted(result)
        host_data = self.get_host_data(contacted)

        total = host_data['swap']['total']
        free = host_data['swap']['free']

        extra = {
            'total': total,
            'free': free,
        }

        level = const.LEVEL_OK
        if total:
            free_percent = int((float(free) / float(total)) * 100)
            used_percent = 100 - free_percent
            extra['used_percent'] = used_percent

            if used_percent >= fail_percent:
                level = const.LEVEL_FAIL
            elif used_percent >= warning_percent:
                level = const.LEVEL_WARNING

        return CheckResult(
            level=level,
            extra=extra,
        )


class DiskSpaceMonit(HostFactsMonit):

    name = 'ansible.disk_space'
    description = 'Ansible disk space host checking. Options: \n' \
                  ' - partitions. Optional. Array with partition names for checking. ' \
                  'For example: ["/", "/var", "/tmp"] \n' \
                  ' - warning. Optional. Percents. Default 80. \n' \
                  ' - fail. Optional. Percents. Default 95.'

    def process_contacted(self, result, kwargs):
        partitions = kwargs.get('partitions')
        warning_percent = int(kwargs.get('warning', 80))
        fail_percent = int(kwargs.get('fail', 95))

        contacted = self._get_contacted(result)
        host_data = self.get_host_data(contacted)

        extra = self._analyze_spaces(host_data['mounts'], partitions, warning_percent, fail_percent)

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

    @staticmethod
    def _analyze_spaces(mounts_data, partitions, warning_percent, fail_percent):
        extra = {'spaces': []}

        for item in mounts_data:
            if partitions and item['mount'] not in partitions:
                continue

            free = item['size_available']
            total = item['size_total']
            free_percent = int((float(free) / float(total)) * 100)
            used_percent = 100 - free_percent

            partition_data = {
                'partition': item['mount'],
                'used_percent': used_percent,
                'free_gb': int(free/1000000000),
                'total_gb': int(total/1000000000),
            }

            if used_percent >= warning_percent:
                used_info = {'partition': item['mount'], 'used_percent': used_percent}
                if used_percent >= fail_percent:
                    extra.setdefault('fails', []).append(used_info)
                elif used_percent >= warning_percent:
                    extra.setdefault('warnings', []).append(used_info)

            extra['spaces'].append(partition_data)

        return extra


