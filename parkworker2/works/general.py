# coding: utf-8
import json
from bson import json_util
import ansible.runner
from parkworker.work import Work
from parkworker.task_processor import TaskResult
from parkworker2.base import AnsibleMixin


class RemoteCommandWork(AnsibleMixin, Work):
    name = 'general.remote_command'
    description = 'Remote command work. Options: \n' \
                  ' - command. Script for running. \n' \
                  ' - is_adapted. Optional. Is output of script adapted for park-keeper ' \
                  '(use TaskResult.get_json() output format). \n' \
                  ' - cwd. Optional. Set current working directory.'

    def run(self, host, remote_user, remote_pass, inventory, kwargs):
        command = kwargs['command']

        cwd = kwargs.get('cwd')
        if cwd:
            command += ' chdir=%s' % cwd

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
        if kwargs.get('is_adapted'):
            contacted = self._get_contacted(result)
            stdout = contacted['stdout']
            parsed_stdout = json.loads(stdout.decode('utf-8'), object_hook=json_util.object_hook)
            return TaskResult(**parsed_stdout)
        else:
            return super(RemoteCommandWork, self).process_contacted(result, kwargs)
