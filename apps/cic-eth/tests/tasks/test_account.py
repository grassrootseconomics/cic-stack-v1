# standard imports
import os
import logging
import time

# third-party imports
import pytest
import web3
import celery

# local imports
from cic_eth.error import OutOfGasError
from cic_eth.db.models.otx import Otx
from cic_eth.db.models.base import SessionBase
from cic_eth.db.enum import StatusEnum
from cic_eth.db.enum import StatusEnum
from cic_eth.db.models.nonce import Nonce
from cic_eth.db.models.role import AccountRole
from cic_eth.eth.account import AccountTxFactory

logg = logging.getLogger() #__name__)


def test_create_account(
        default_chain_spec,
        init_w3,
        init_database,
        celery_session_worker,
        ):
    
    s = celery.signature(
            'cic_eth.eth.account.create',
            [
                'foo',
                str(default_chain_spec),
                ],
            )
    t = s.apply_async()
    r = t.get()
    logg.debug('got account {}'.format(r))

    session = SessionBase.create_session()
    q = session.query(Nonce).filter(Nonce.address_hex==r)
    o = q.first()
    logg.debug('oooo s {}'.format(o))
    session.close()
    assert o != None
    assert o.nonce == 0

    s = celery.signature(
            'cic_eth.eth.account.have',
            [
                r,
                str(default_chain_spec),
            ],
            )
    t = s.apply_async()
    assert r == t.get()


def test_register_account(
        default_chain_spec,
        accounts_registry,
        init_database,
        init_eth_tester,
        init_w3,
        cic_registry,
        celery_session_worker,
        eth_empty_accounts,
        ):

    logg.debug('chainspec {}'.format(str(default_chain_spec)))

    s = celery.signature(
            'cic_eth.eth.account.register',
            [
                eth_empty_accounts[0],
                str(default_chain_spec),
                init_w3.eth.accounts[0],
                ],
            )
    t = s.apply_async()
    address = t.get()
    r = t.collect()
    t.successful()

    session = SessionBase.create_session()
    o = session.query(Otx).first()
    tx_signed_hex = o.signed_tx
    session.close()
    
    s_send = celery.signature(
            'cic_eth.eth.tx.send',
            [
                [tx_signed_hex],
                str(default_chain_spec),
            ],
            )
    t = s_send.apply_async()
    address = t.get()
    r = t.collect()
    t.successful()

    init_eth_tester.mine_block()

    assert accounts_registry.have(eth_empty_accounts[0])


def test_role_task(
    init_database,
    celery_session_worker,
    default_chain_spec,
        ):

    address = '0x' + os.urandom(20).hex()
    role = AccountRole.set('foo', address)
    init_database.add(role)
    init_database.commit()
    s = celery.signature(
            'cic_eth.eth.account.role',
            [
                address,
                str(default_chain_spec), 
                ],
            )
    t = s.apply_async()
    r = t.get()
    assert r == 'foo'
