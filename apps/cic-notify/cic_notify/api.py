# standard imports
import logging
import re

# third-party imports
import celery

# local imports
from cic_notify.tasks import sms

app = celery.current_app
logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

sms_tasks_matcher = r"^(cic_notify.tasks.sms)(\.\w+)?"


class Api:
    # TODO: Implement callback strategy
    def __init__(self, queue='cic-notify'):
        """
        :param queue: The queue on which to execute notification tasks
        :type queue: str
        """
        registered_tasks = app.tasks
        self.sms_tasks = []

        for task in registered_tasks.keys():
            logg.debug(f'Found: {task} {registered_tasks[task]}')
            match = re.match(sms_tasks_matcher, task)
            if match:
                self.sms_tasks.append(task)

        self.queue = queue
        logg.info(f'api using queue: {self.queue}')

    def sms(self, message, recipient):
        """This function chains all sms tasks in order to send a message, log and persist said data to disk
        :param message: The message to be sent to the recipient.
        :type message: str
        :param recipient: The phone number of the recipient.
        :type recipient: str
        :return: a celery Task
        :rtype: Celery.Task
        """
        signatures = []
        for task in self.sms_tasks:
            signature = celery.signature(task)
            signatures.append(signature)
            signature_group = celery.group(signatures)
            result = signature_group.apply_async(
                args=[message, recipient],
                queue=self.queue
            )
            return result
