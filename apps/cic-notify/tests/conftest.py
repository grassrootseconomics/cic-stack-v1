# standard imports
import sys
import os
import pytest
import logging

# third party imports
import confini

script_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.insert(0, root_dir)

# local imports
from cic_notify.db.models.base import SessionBase
#from transport.notification import AfricastalkingNotification

# fixtures
from tests.fixtures_config import *
from tests.fixtures_celery import *
from tests.fixtures_database import *

logg = logging.getLogger()


#@pytest.fixture(scope='session')
#def africastalking_notification(
#        load_config,
#        ):
#    return AfricastalkingNotificationTransport(load_config)
#
