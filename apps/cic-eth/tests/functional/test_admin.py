# standard imports
import os
import logging

# third-party imports
import celery
import pytest
import web3

# local imports
from cic_eth.api import AdminApi
from cic_eth.db.models.role import AccountRole
from cic_eth.db.enum import (
        StatusEnum,
        StatusBits,
        status_str,
        )
from cic_eth.error import InitializationError
from cic_eth.eth.task import sign_and_register_tx
from cic_eth.eth.tx import cache_gas_refill_data
from cic_eth.eth.util import unpack_signed_raw_tx
from cic_eth.eth.rpc import RpcClient
from cic_eth.eth.task import sign_tx
from cic_eth.eth.tx import otx_cache_parse_tx
from cic_eth.queue.tx import create as queue_create
from cic_eth.queue.tx import get_tx

logg = logging.getLogger()


def test_resend_inplace(
    default_chain_spec,
    init_database,
    init_w3,
    celery_session_worker,
    ):
    
    chain_str = str(default_chain_spec)
    c = RpcClient(default_chain_spec)
    
    sigs = []
    s = celery.signature(
        'cic_eth.eth.tx.refill_gas',
        [
            init_w3.eth.accounts[0],
            chain_str,
            ],
        queue=None,
            )
    t = s.apply_async()
    tx_raw = t.get()
    assert t.successful()

    tx_dict = unpack_signed_raw_tx(bytes.fromhex(tx_raw[2:]), default_chain_spec.chain_id())
    gas_price_before = tx_dict['gasPrice'] 

    s = celery.signature(
        'cic_eth.admin.ctrl.lock_send',
        [
            chain_str,
            init_w3.eth.accounts[0],
            ],
        queue=None,
            )
    t = s.apply_async()
    t.get()
    assert t.successful()

    api = AdminApi(c, queue=None)
    t = api.resend(tx_dict['hash'], chain_str, unlock=True)
    t.get()
    i = 0
    tx_hash_new_hex = None
    for r in t.collect():
        tx_hash_new_hex = r[1]
    assert t.successful()
  
    tx_raw_new = get_tx(tx_hash_new_hex) 
    logg.debug('get {}'.format(tx_raw_new))
    tx_dict_new = unpack_signed_raw_tx(bytes.fromhex(tx_raw_new['signed_tx'][2:]), default_chain_spec.chain_id())
    assert tx_hash_new_hex != tx_dict['hash']
    assert tx_dict_new['gasPrice'] > gas_price_before

    tx_dict_after = get_tx(tx_dict['hash'])

    logg.debug('logggg {}'.format(status_str(tx_dict_after['status'])))
    assert tx_dict_after['status'] & StatusBits.MANUAL


#def test_check_fix_nonce(
#    default_chain_spec,
#    init_database,
#    init_eth_account_roles,
#    init_w3,
#    eth_empty_accounts,
#    celery_session_worker,
#    ):
#
#    chain_str = str(default_chain_spec)
#    
#    sigs = []
#    for i in range(5):
#        s = celery.signature(
#            'cic_eth.eth.tx.refill_gas',
#            [
#                eth_empty_accounts[i],
#                chain_str,
#                ],
#            queue=None,
#                )
#        sigs.append(s)
#
#    t = celery.group(sigs)()
#    txs = t.get()
#    assert t.successful()
#
#    tx_hash = web3.Web3.keccak(hexstr=txs[2])
#    c = RpcClient(default_chain_spec)
#    api = AdminApi(c, queue=None)
#    address = init_eth_account_roles['eth_account_gas_provider']
#    nonce_spec = api.check_nonce(address)
#    assert nonce_spec['nonce']['network'] == 0
#    assert nonce_spec['nonce']['queue'] == 4
#    assert nonce_spec['nonce']['blocking'] == None
#
#    s_set = celery.signature(
#            'cic_eth.queue.tx.set_rejected',
#            [
#                tx_hash.hex(),
#                ],
#            queue=None,
#            )
#    t = s_set.apply_async()
#    t.get()
#    t.collect()
#    assert t.successful()
#
#
#    nonce_spec = api.check_nonce(address)
#    assert nonce_spec['nonce']['blocking'] == 2
#    assert nonce_spec['tx']['blocking'] == tx_hash.hex()
#
#    t = api.fix_nonce(address, nonce_spec['nonce']['blocking'])
#    t.get()
#    t.collect()
#    assert t.successful()
#
#    for tx in txs[3:]:
#        tx_hash = web3.Web3.keccak(hexstr=tx)
#        tx_dict = get_tx(tx_hash.hex())
#        assert tx_dict['status'] == StatusEnum.OVERRIDDEN
#
#
#def test_tag_account(
#    init_database,
#    eth_empty_accounts,
#    init_rpc,
#    ):
#
#    api = AdminApi(init_rpc)
#
#    api.tag_account('foo', eth_empty_accounts[0])
#    api.tag_account('bar', eth_empty_accounts[1])
#    api.tag_account('bar', eth_empty_accounts[2])
#
#    assert AccountRole.get_address('foo') == eth_empty_accounts[0]
#    assert AccountRole.get_address('bar') == eth_empty_accounts[2]
#
#
#def test_ready(
#    init_database,
#    eth_empty_accounts,
#    init_rpc,
#    w3,
#    ):
#
#    api = AdminApi(init_rpc)
#   
#    with pytest.raises(InitializationError):
#        api.ready()
#
#    bogus_account = os.urandom(20)
#    bogus_account_hex = '0x' + bogus_account.hex()
#
#    api.tag_account('ETH_GAS_PROVIDER_ADDRESS', web3.Web3.toChecksumAddress(bogus_account_hex))
#    with pytest.raises(KeyError):
#        api.ready()
#
#    api.tag_account('ETH_GAS_PROVIDER_ADDRESS', eth_empty_accounts[0])
#    api.ready()
#
#
#def test_tx(
#    default_chain_spec,
#    cic_registry,
#    init_database,
#    init_rpc,
#    init_w3,
#    celery_session_worker,
#        ):
#
#    tx = {
#        'from': init_w3.eth.accounts[0],
#        'to': init_w3.eth.accounts[1],
#        'nonce': 42,
#        'gas': 21000,
#        'gasPrice': 1000000,
#        'value': 128,
#        'chainId': default_chain_spec.chain_id(),
#        'data': '',
#        }
#
#    (tx_hash_hex, tx_signed_raw_hex) = sign_tx(tx, str(default_chain_spec))
#    queue_create(
#        tx['nonce'],
#        tx['from'],
#        tx_hash_hex,
#        tx_signed_raw_hex,
#        str(default_chain_spec),
#            )
#    tx_recovered = unpack_signed_raw_tx(bytes.fromhex(tx_signed_raw_hex[2:]), default_chain_spec.chain_id())
#    cache_gas_refill_data(tx_hash_hex, tx_recovered)
#
#    api = AdminApi(init_rpc, queue=None)
#    tx = api.tx(default_chain_spec, tx_hash=tx_hash_hex)
