# standard imports
import json
import logging
from typing import Union

# third-party imports
import celery
from cic_eth.api import Api

# local imports
from cic_ussd.error import CachedDataNotFoundError
from cic_ussd.redis import create_cached_data_key, get_cached_data
from cic_ussd.conversions import from_wei

logg = logging.getLogger()


def get_balances(
        address: str,
        chain_str: str,
        token_symbol: str,
        asynchronous: bool = False,
        callback_param: any = None,
        callback_task='cic_ussd.tasks.callback_handler.process_balances_callback') -> Union[celery.Task, dict]:
    """
    This function queries cic-eth for an account's balances, It provides a means to receive the balance either
    asynchronously or synchronously depending on the provided value for teh asynchronous parameter. It returns a
    dictionary containing network, outgoing and incoming balances.
    :param address: Ethereum address of the recipient
    :type address: str, 0x-hex
    :param chain_str: The chain name and network id.
    :type chain_str: str
    :param callback_param:
    :type callback_param:
    :param callback_task:
    :type callback_task:
    :param token_symbol: ERC20 token symbol of the account whose balance is being queried.
    :type token_symbol: str
    :param asynchronous: Boolean value checking whether to return balances asynchronously.
    :type asynchronous: bool
    :return:
    :rtype:
    """
    logg.debug(f'Retrieving balance for address: {address}')
    if asynchronous:
        cic_eth_api = Api(
            chain_str=chain_str,
            callback_queue='cic-ussd',
            callback_task=callback_task,
            callback_param=callback_param
        )
        cic_eth_api.balance(address=address, token_symbol=token_symbol)
    else:
        cic_eth_api = Api(chain_str=chain_str)
        balance_request_task = cic_eth_api.balance(
            address=address,
            token_symbol=token_symbol)
        return balance_request_task.get()[0]


def compute_operational_balance(balances: dict) -> float:
    """This function calculates the right balance given incoming and outgoing
    :param balances:
    :type balances:
    :return:
    :rtype:
    """
    incoming_balance = balances.get('balance_incoming')
    outgoing_balance = balances.get('balance_outgoing')
    network_balance = balances.get('balance_network')

    operational_balance = (network_balance + incoming_balance) - outgoing_balance
    return from_wei(value=operational_balance)


def get_cached_operational_balance(blockchain_address: str):
    """
    :param blockchain_address:
    :type blockchain_address:
    :return:
    :rtype:
    """
    key = create_cached_data_key(
        identifier=bytes.fromhex(blockchain_address[2:]),
        salt=':cic.balances_data'
    )
    cached_balance = get_cached_data(key=key)
    if cached_balance:
        operational_balance = compute_operational_balance(balances=json.loads(cached_balance))
        return operational_balance
    else:
        raise CachedDataNotFoundError('Cached operational balance not found.')
