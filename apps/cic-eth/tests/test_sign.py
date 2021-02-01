# standard imports
import logging
import sha3

# third-party imports
import pytest

logg = logging.getLogger()


def test_sign(
    init_w3,
    init_eth_tester,
    ):
    nonce = init_w3.eth.getTransactionCount(init_w3.eth.accounts[0], 'pending')
    tx = init_w3.eth.sign_transaction({
        'from': init_w3.eth.accounts[0],
        'to': init_w3.eth.accounts[1],
        'nonce': nonce,
        'value': 101,
        'gasPrice': 2000000000,
        'gas': 21000,
        'data': '',
        'chainId': 8995,
        })
    tx_hash = init_w3.eth.send_raw_transaction(tx['raw'])
    logg.debug('have tx {}'.format(tx_hash))
