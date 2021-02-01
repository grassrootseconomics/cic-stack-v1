# standard imports
import os
import json
import logging 

# third-party imports
import celery

# local imports
from cic_eth.eth.account import unpack_gift
from cic_eth.eth.factory import TxFactory
from cic_eth.eth.util import unpack_signed_raw_tx

logg = logging.getLogger()

script_dir = os.path.dirname(__file__)


def test_faucet(
    default_chain_spec,
    faucet_amount,
    faucet,
    eth_empty_accounts,
    bancor_tokens,
    w3_account_roles,
    w3_account_token_owners,
    init_w3,
    solidity_abis,
    init_eth_tester,
    cic_registry,
    celery_session_worker,
    init_database,
        ):

    s = celery.signature(
        'cic_eth.eth.account.gift',
        [
            init_w3.eth.accounts[7],
            str(default_chain_spec),
            ],
            )     
    s_send = celery.signature(
        'cic_eth.eth.tx.send',
        [
            str(default_chain_spec),
            ],
        )
    s.link(s_send)
    t = s.apply_async()
    signed_tx = t.get()
    for r in t.collect():
        logg.debug('result {}'.format(r))

    assert t.successful()

    tx = unpack_signed_raw_tx(bytes.fromhex(signed_tx[0][2:]), default_chain_spec.chain_id())
    giveto = unpack_gift(tx['data'])
    assert giveto['to'] == init_w3.eth.accounts[7]

    init_eth_tester.mine_block()

    token = init_w3.eth.contract(abi=solidity_abis['ERC20'], address=bancor_tokens[0])

    balance = token.functions.balanceOf(init_w3.eth.accounts[7]).call()

    assert balance == faucet_amount
