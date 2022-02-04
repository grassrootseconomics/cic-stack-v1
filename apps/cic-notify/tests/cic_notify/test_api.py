# standard imports

# external imports
import celery

# local imports
from cic_notify.api import Api
from cic_notify.mux import Muxer

# test imports
from tests.helpers.phone import phone_number


def notify_provisions(mocker):
    mocked_group = mocker.patch('celery.group')
    message = 'Hello world.'
    recipient = phone_number()
    return mocked_group, message, recipient


def celery_signatures(message, recipient):
    s_log = celery.signature('cic_notify.tasks.default.log.log', [message, recipient], queue=None)
    s_persist_notification = celery.signature(
            'cic_notify.tasks.default.db.persist_notification', [message, recipient], queue=None)
    s_send = celery.signature('cic_notify.tasks.sms.africastalking.send', [message, recipient], queue=None)
    return s_log, s_persist_notification, s_send


def test_api(celery_session_worker, mocker):
    mocked_group, message, recipient = notify_provisions(mocker)
    s_log, s_persist_notification, s_send = celery_signatures(message, recipient)
    signatures = [s_persist_notification, s_log]
    api = Api(queue=None)
    api.notify(message, recipient)
    mocked_group.assert_called_with(signatures)


def test_api_with_specified_channel(mocker):
    Muxer.tasks.append('cic_notify.tasks.sms.africastalking.send')
    mocked_group, message, recipient = notify_provisions(mocker)
    s_log, s_persist_notification, s_send = celery_signatures(message, recipient)
    api = Api(channel_keys=['sms'], queue=None)
    api.notify(message, recipient)
    signatures = [s_persist_notification, s_log, s_send]
    mocked_group.assert_called_with(signatures)
