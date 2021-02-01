# standard imports
import logging
import os

# third-party imports
import celery
import pytest

# local imports
import cic_eth
from cic_eth.db.models.lock import Lock
from cic_eth.db.enum import StatusEnum
from cic_eth.db.enum import LockEnum
from cic_eth.error import LockedError
from cic_eth.queue.tx import create as queue_create
from cic_eth.queue.tx import set_sent_status
from cic_eth.eth.tx import cache_gas_refill_data
from cic_eth.error import PermanentTxError
from cic_eth.queue.tx import get_tx
from cic_eth.eth.task import sign_tx

logg = logging.getLogger()


# TODO: There is no
def test_send_reject(
        default_chain_spec,
        init_w3,
        mocker,
        init_database,
        celery_session_worker,
        ):

    nonce = init_w3.eth.getTransactionCount(init_w3.eth.accounts[0], 'pending')
    tx = {
        'from': init_w3.eth.accounts[0],
        'to': init_w3.eth.accounts[1],
        'nonce': nonce,
        'gas': 21000,
        'gasPrice': 1000000,
        'value': 128,
        'chainId': default_chain_spec.chain_id(),
        'data': '',
        }

    chain_str = str(default_chain_spec)

    (tx_hash_hex, tx_signed_raw_hex) = sign_tx(tx, chain_str)
    queue_create(tx['nonce'], tx['from'], tx_hash_hex, tx_signed_raw_hex, str(default_chain_spec))
    cache_gas_refill_data(tx_hash_hex, tx)
    s = celery.signature(
            'cic_eth.eth.tx.send',
            [
                [tx_signed_raw_hex],
                chain_str,
                ],
            )
    t = s.apply_async()
    r = t.get()
    

def test_sync_tx(
    default_chain_spec,
    init_database,
    init_w3,
    init_wallet_extension,
    init_eth_tester,
    celery_session_worker,
    eth_empty_accounts,
    ):

    nonce = init_w3.eth.getTransactionCount(init_w3.eth.accounts[0], 'pending')
    tx = {
        'from': init_w3.eth.accounts[0],
        'to': init_w3.eth.accounts[1],
        'nonce': nonce,
        'gas': 21000,
        'gasPrice': 1000000,
        'value': 128,
        'chainId': default_chain_spec.chain_id(),
        'data': '',
        }

    chain_str = str(default_chain_spec)

    (tx_hash_hex, tx_signed_raw_hex) = sign_tx(tx, chain_str)
    queue_create(tx['nonce'], tx['from'], tx_hash_hex, tx_signed_raw_hex, str(default_chain_spec))
    cache_gas_refill_data(tx_hash_hex, tx)

    init_w3.eth.send_raw_transaction(tx_signed_raw_hex)

    s = celery.signature(
            'cic_eth.eth.tx.sync_tx',
            [
                tx_hash_hex,
                chain_str,
                ],
            queue=None
            )
    t = s.apply_async()
    r = t.get()
    for _ in t.collect():
        pass
    assert t.successful()

    tx_dict = get_tx(tx_hash_hex)
    assert tx_dict['status'] == StatusEnum.SENT

    init_eth_tester.mine_block() 

    s = celery.signature(
            'cic_eth.eth.tx.sync_tx',
            [
                tx_hash_hex,
                chain_str,
                ],
            queue=None
            )
    t = s.apply_async()
    r = t.get()
    for _ in t.collect():
        pass
    assert t.successful()

    tx_dict = get_tx(tx_hash_hex)
    assert tx_dict['status'] == StatusEnum.SUCCESS



def test_resume_tx(
    default_chain_spec,
    init_database,
    init_w3,
    celery_session_worker,
        ):

    tx = {
        'from': init_w3.eth.accounts[0],
        'to': init_w3.eth.accounts[1],
        'nonce': 42 ,
        'gas': 21000,
        'gasPrice': 1000000,
        'value': 128,
        'chainId': default_chain_spec.chain_id(),
        'data': '',
        }
    tx_signed = init_w3.eth.sign_transaction(tx)
    tx_hash = init_w3.keccak(hexstr=tx_signed['raw'])
    tx_hash_hex = tx_hash.hex()
    queue_create(tx['nonce'], tx['from'], tx_hash_hex, tx_signed['raw'], str(default_chain_spec))
    cache_gas_refill_data(tx_hash_hex, tx)

    set_sent_status(tx_hash_hex, True)

    s = celery.signature(
            'cic_eth.eth.tx.resume_tx',
            [
                tx_hash_hex,
                str(default_chain_spec),
                ],
            )
    t = s.apply_async()
    t.get()
    for r in t.collect():
        logg.debug('collect {}'.format(r))
    assert t.successful()


