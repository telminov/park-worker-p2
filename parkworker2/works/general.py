# coding: utf-8
import ansible.runner
from parkworker.work import Work
from parkworker2.base import AnsibleMixin


class RemoteCommandWork(AnsibleMixin, Work):
    name = 'general.remote_command'
    description = 'Remote command work. Options: \n' \
                  ' - command. Script for running. \n'

    def run(self, host, remote_user, remote_pass, inventory, kwargs):
        command = kwargs['command']

        runner = ansible.runner.Runner(
            module_name='shell',
            module_args=command,
            inventory=inventory,
            pattern=host,
            remote_user=remote_user, remote_pass=remote_pass
        )
        result = runner.run()
        return result
