# standard imports
import logging
import os

# external imports
import celery

# local imports
from cic_notify.mux import Muxer

app = celery.current_app
logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

root_directory = os.path.dirname(__file__)
default_config_directory = os.path.join(root_directory, 'data', 'config', 'tasks')


# initialize muxer
Muxer.initialize(default_config_directory)


class Api:
    def __init__(self, channel_keys=None, queue: any = 'cic-notify'):
        """
        :param queue: The queue on which to execute notification tasks.
        :type queue: str
        """
        if channel_keys is None:
            channel_keys = []
        self.channel_keys = channel_keys
        self.queue = queue

    def notify(self, message: str, recipient: str):
        """
        :param message:
        :type message:
        :param recipient:
        :type recipient:
        :return:
        :rtype:
        """

        muxer = Muxer()
        muxer.route(channel_keys=self.channel_keys)

        signatures = []
        for task in muxer.tasks:
            signature = celery.signature(task, [message, recipient, ], queue=self.queue)
            signatures.append(signature)
        return celery.group(signatures)()
