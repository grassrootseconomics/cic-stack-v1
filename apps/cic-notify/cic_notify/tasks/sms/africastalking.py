# standard imports
import logging

# third party imports
import celery
import africastalking

# local imports
from cic_notify.error import NotInitializedError, AlreadyInitializedError

logg = logging.getLogger()
celery_app = celery.current_app


class AfricasTalkingNotifier:
    initiated = None
    sender_id = None

    def __init__(self):
        if not self.initiated:
            raise NotInitializedError()
        self.api_client = africastalking.SMS

    @staticmethod
    def initialize(api_username, api_key, sender_id=None):
        """
        :param api_username:
        :type api_username:
        :param api_key:
        :type api_key:
        :param sender_id:
        :type sender_id:
        """
        if AfricasTalkingNotifier.initiated:
            raise AlreadyInitializedError()
        africastalking.initialize(username=api_username, api_key=api_key)

        AfricasTalkingNotifier.sender_id = sender_id
        AfricasTalkingNotifier.initiated = True

    def send(self, message, recipient):
        """
        :param message:
        :type message:
        :param recipient:
        :type recipient:
        :return:
        :rtype:
        """
        if self.sender_id:
            response = self.api_client.send(message=message, recipients=[recipient], sender_id=self.sender_id)
            logg.debug(f'Africastalking response sender-id {response}')
        else:
            response = self.api_client.send(message=message, recipients=[recipient])
            logg.debug(f'africastalking response no-sender-id {response}')


@celery_app.task
def send(message, recipient):
    """
    :param message:
    :type message:
    :param recipient:
    :type recipient:
    :return:
    :rtype:
    """
    africastalking_notifier = AfricasTalkingNotifier()
    africastalking_notifier.send(message=message, recipient=recipient)
