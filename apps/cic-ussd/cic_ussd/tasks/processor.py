# standard imports
import logging

# third-party imports
import celery
from i18n import config

# local imports
from cic_ussd.account import define_account_tx_metadata
from cic_ussd.db.models.account import Account
from cic_ussd.db.models.base import SessionBase
from cic_ussd.error import UnknownUssdRecipient
from cic_ussd.transactions import from_wei


celery_app = celery.current_app
logg = logging.getLogger(__file__)


@celery_app.task
def process_tx_metadata_for_notification(result: celery.Task, transaction_metadata: dict):
    """
    :param result:
    :type result:
    :param transaction_metadata:
    :type transaction_metadata:
    :return:
    :rtype:
    """
    notification_data = {}

    # get preferred language
    preferred_language = result.get('preferred_language')
    if not preferred_language:
        preferred_language = config.get('fallback')
    notification_data['preferred_language'] = preferred_language

    # validate account information against present ussd storage data.
    session = SessionBase.create_session()
    blockchain_address = transaction_metadata.get('blockchain_address')
    tag = transaction_metadata.get('tag')
    account = session.query(Account).filter_by(blockchain_address=blockchain_address).first()
    if not account and tag == 'recipient':
        session.close()
        raise UnknownUssdRecipient(
            f'Tx for recipient: {blockchain_address} was received but has no matching user in the system.'
        )

    # get phone number associated with account
    phone_number = account.phone_number
    notification_data['phone_number'] = phone_number

    # get account's role in transaction i.e sender / recipient
    tx_param = transaction_metadata.get('tx_param')
    notification_data['transaction_type'] = tx_param

    # get token amount and symbol
    if tag == 'recipient':
        account_tx_role = tag
        amount = transaction_metadata.get('token_value')
        amount = from_wei(value=amount)
        token_symbol = transaction_metadata.get('token_symbol')
    else:
        account_tx_role = tag
        amount = transaction_metadata.get('token_value')
        amount = from_wei(value=amount)
        token_symbol = transaction_metadata.get('token_symbol')
    notification_data['account_tx_role'] = account_tx_role
    notification_data['amount'] = amount
    notification_data['token_symbol'] = token_symbol

    # get account's standard ussd identification pattern
    if tx_param == 'transfer':
        tx_account_metadata = define_account_tx_metadata(user=account)
        notification_data['transaction_account_metadata'] = tx_account_metadata

        if tag == 'recipient':
            notification_data['notification_key'] = 'sms.received_tokens'
        else:
            notification_data['notification_key'] = 'sms.sent_tokens'

    if tx_param == 'tokengift':
        notification_data['notification_key'] = 'sms.account_successfully_created'

    # get account's balance
    notification_data['balance'] = transaction_metadata.get('operational_balance')

    return notification_data
