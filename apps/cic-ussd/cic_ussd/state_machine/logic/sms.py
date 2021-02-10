# standard imports
import logging
from typing import Tuple

# local imports
from cic_ussd.db.models.user import User

logg = logging.getLogger()


def send_terms_to_user_if_required(state_machine_data: Tuple[str, dict, User]):
    user_input, ussd_session, user = state_machine_data
    logg.debug('Requires integration to cic-notify.')


def process_mini_statement_request(state_machine_data: Tuple[str, dict, User]):
    user_input, ussd_session, user = state_machine_data
    logg.debug('Requires integration to cic-notify.')


def upsell_unregistered_recipient(state_machine_data: Tuple[str, dict, User]):
    user_input, ussd_session, user = state_machine_data
    logg.debug('Requires integration to cic-notify.')