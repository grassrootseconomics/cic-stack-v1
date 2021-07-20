# standard imports
import datetime
import logging

# third-party imports
import celery

# local imports
from cic_ussd.notifications import Notifier
from cic_ussd.phone_number import Support

celery_app = celery.current_app
logg = logging.getLogger(__file__)
notifier = Notifier()


@celery_app.task
def notify_account_of_transaction(notification_data: dict):
    """
    :param notification_data:
    :type notification_data:
    :return:
    :rtype:
    """

    account_tx_role = notification_data.get('account_tx_role')
    amount = notification_data.get('amount')
    balance = notification_data.get('balance')
    phone_number = notification_data.get('phone_number')
    preferred_language = notification_data.get('preferred_language')
    token_symbol = notification_data.get('token_symbol')
    transaction_account_metadata = notification_data.get('transaction_account_metadata')
    transaction_type = notification_data.get('transaction_type')

    timestamp = datetime.datetime.now().strftime('%d-%m-%y, %H:%M %p')

    if transaction_type == 'tokengift':
        support_phone = Support.phone_number
        notifier.send_sms_notification(
            key='sms.account_successfully_created',
            phone_number=phone_number,
            preferred_language=preferred_language,
            balance=balance,
            support_phone=support_phone,
            token_symbol=token_symbol
        )

    if transaction_type == 'transfer':
        if account_tx_role == 'recipient':
            notifier.send_sms_notification(
                key='sms.received_tokens',
                phone_number=phone_number,
                preferred_language=preferred_language,
                amount=amount,
                token_symbol=token_symbol,
                tx_sender_information=transaction_account_metadata,
                timestamp=timestamp,
                balance=balance
            )
        else:
            notifier.send_sms_notification(
                key='sms.sent_tokens',
                phone_number=phone_number,
                preferred_language=preferred_language,
                amount=amount,
                token_symbol=token_symbol,
                tx_recipient_information=transaction_account_metadata,
                timestamp=timestamp,
                balance=balance
            )
