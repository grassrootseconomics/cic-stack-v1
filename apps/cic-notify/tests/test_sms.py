# standard imports
import json

# third party imports
import pytest
import celery

# local imports
from cic_notify.tasks.sms import db
from cic_notify.tasks.sms import log

def test_log_notification(
    celery_session_worker,
        ):

    recipient = '+25412121212'
    content = 'bar'
    s_log = celery.signature('cic_notify.tasks.sms.log.log')
    t = s_log.apply_async(args=[recipient, content])

    r = t.get()


def test_db_notification(
    init_database,
    celery_session_worker,
        ):

    recipient = '+25412121213'
    content = 'foo'
    s_db = celery.signature('cic_notify.tasks.sms.db.persist_notification')
    t = s_db.apply_async(args=[recipient, content])

    r = t.get()
