# standard imports
import os
import logging

# external imports
import celery
import pytest
from chainlib.eth.tx import (
        unpack,
        TxFormat,
        )
from chainlib.eth.nonce import (
        RPCNonceOracle,
        OverrideNonceOracle,
        )
from chainlib.eth.gas import (
        Gas,
        OverrideGasOracle,
        )
from chainlib.eth.address import to_checksum_address
from hexathon import (
        strip_0x,
        add_0x,
        )
from chainqueue.db.models.otx import Otx
from chainqueue.db.models.tx import TxCache
from chainqueue.db.enum import (
        StatusEnum,
        StatusBits,
        status_str,
        )
from chainqueue.sql.state import (
        set_fubar,
        set_ready,
        set_reserved,
        )

# local imports
from cic_eth.api.admin import AdminApi
from cic_eth.db.models.role import AccountRole
from cic_eth.db.enum import LockEnum
from cic_eth.error import InitializationError
from cic_eth.eth.gas import cache_gas_data
from cic_eth.queue.tx import queue_create
from cic_eth.queue.query import (
        get_tx,
        get_nonce_tx_local,
        )
from cic_eth.encode import tx_normalize

logg = logging.getLogger()


def test_have_account(
    default_chain_spec,
    custodial_roles,
    init_celery_tasks,
    eth_rpc,
    celery_session_worker,
    ):

    api = AdminApi(None, queue=None)
    t = api.have_account(custodial_roles['ALICE'], default_chain_spec)
    assert t.get() != None 

    bogus_address = add_0x(to_checksum_address(os.urandom(20).hex()))
    api = AdminApi(None, queue=None)
    t = api.have_account(bogus_address, default_chain_spec)
    assert t.get() == None


def test_locking(
    default_chain_spec,
    init_database,
    agent_roles,
    init_celery_tasks,
    celery_session_worker,
    ):

    api = AdminApi(None, queue=None)

    t = api.lock(default_chain_spec, agent_roles['ALICE'], LockEnum.SEND)
    t.get()
    t = api.get_lock()
    r = t.get()
    assert len(r) == 1

    t = api.unlock(default_chain_spec, agent_roles['ALICE'], LockEnum.SEND)
    t.get()
    t = api.get_lock()
    r = t.get()
    assert len(r) == 0


def test_tag_account(
    default_chain_spec,
    init_database,
    agent_roles,
    eth_rpc,
    init_celery_tasks,
    celery_session_worker,
    ):

    api = AdminApi(eth_rpc, queue=None)

    t = api.tag_account(default_chain_spec, 'foo', agent_roles['ALICE'])
    t.get()
    t = api.tag_account(default_chain_spec, 'bar', agent_roles['BOB'])
    t.get()
    t = api.tag_account(default_chain_spec, 'bar', agent_roles['CAROL'])
    t.get()

    assert AccountRole.get_address('foo', init_database) == tx_normalize.wallet_address(agent_roles['ALICE'])
    assert AccountRole.get_address('bar', init_database) == tx_normalize.wallet_address(agent_roles['CAROL'])


def test_tx(
    default_chain_spec,
    cic_registry,
    init_database,
    eth_rpc,
    eth_signer,
    agent_roles,
    contract_roles,
    celery_session_worker,
    ):

    nonce_oracle = RPCNonceOracle(agent_roles['ALICE'], eth_rpc)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle)
    (tx_hash_hex, tx_signed_raw_hex) = c.create(agent_roles['ALICE'], agent_roles['BOB'], 1024, tx_format=TxFormat.RLP_SIGNED)
    tx = unpack(bytes.fromhex(strip_0x(tx_signed_raw_hex)), default_chain_spec)
    queue_create(default_chain_spec, tx['nonce'], agent_roles['ALICE'], tx_hash_hex, tx_signed_raw_hex)
    cache_gas_data(tx_hash_hex, tx_signed_raw_hex, default_chain_spec.asdict())

    api = AdminApi(eth_rpc, queue=None, call_address=contract_roles['DEFAULT'])
    tx = api.tx(default_chain_spec, tx_hash=tx_hash_hex)
    logg.warning('code missing to verify tx contents {}'.format(tx))


def test_check_nonce_gap(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        agent_roles,
        contract_roles,
        celery_session_worker,
        caplog,
        ):

    # NOTE: this only works as long as agents roles start at nonce 0
    nonce_oracle = OverrideNonceOracle(agent_roles['ALICE'], 0)
    gas_oracle = OverrideGasOracle(limit=21000, conn=eth_rpc)

    tx_hashes = []
    txs = []

    j = 0
    for i in range(10):
        c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
        (tx_hash_hex, tx_signed_raw_hex) = c.create(agent_roles['ALICE'], agent_roles['BOB'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)
        if i == 3:
            j = 1
            nonce_oracle = OverrideNonceOracle(agent_roles['ALICE'], i+1)

        queue_create(
                default_chain_spec,
                i+j,
                agent_roles['ALICE'],
                tx_hash_hex,
                tx_signed_raw_hex,
                session=init_database,
                )
        cache_gas_data(
                tx_hash_hex,
                tx_signed_raw_hex,
                default_chain_spec.asdict(),
                )
        tx_hashes.append(tx_hash_hex)
        txs.append(tx_signed_raw_hex)


    init_database.commit()

    api = AdminApi(eth_rpc, queue=None, call_address=contract_roles['DEFAULT'])
    r = api.check_nonce(default_chain_spec, agent_roles['ALICE'])

    assert r['nonce']['blocking'] == 4
    assert r['tx']['blocking'] == tx_hashes[3] # one less because there is a gap


def test_check_nonce_localfail(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        agent_roles,
        contract_roles,
        celery_session_worker,
        caplog,
        ):

    # NOTE: this only works as long as agents roles start at nonce 0
    nonce_oracle = OverrideNonceOracle(agent_roles['ALICE'], 0)
    gas_oracle = OverrideGasOracle(limit=21000, conn=eth_rpc)

    tx_hashes = []
    txs = []

    j = 0
    for i in range(10):
        c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
        (tx_hash_hex, tx_signed_raw_hex) = c.create(agent_roles['ALICE'], agent_roles['BOB'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)

        queue_create(
                default_chain_spec,
                i,
                agent_roles['ALICE'],
                tx_hash_hex,
                tx_signed_raw_hex,
                session=init_database,
                )
        cache_gas_data(
                tx_hash_hex,
                tx_signed_raw_hex,
                default_chain_spec.asdict(),
                )
        tx_hashes.append(tx_hash_hex)
        txs.append(tx_signed_raw_hex)

    set_ready(default_chain_spec, tx_hashes[4], session=init_database)
    set_reserved(default_chain_spec, tx_hashes[4], session=init_database)
    set_fubar(default_chain_spec, tx_hashes[4], session=init_database)

    init_database.commit()

    api = AdminApi(eth_rpc, queue=None, call_address=contract_roles['DEFAULT'])
    r = api.check_nonce(default_chain_spec, agent_roles['ALICE'])

    assert r['nonce']['blocking'] == 4
    assert r['tx']['blocking'] == tx_hashes[4]


def test_fix_nonce(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        agent_roles,
        contract_roles,
        celery_session_worker,
        init_celery_tasks,
        caplog,
        ):

    nonce_oracle = OverrideNonceOracle(agent_roles['ALICE'], 0)
    gas_oracle = OverrideGasOracle(limit=21000, conn=eth_rpc)

    tx_hashes = []
    txs = []

    for i in range(10):
        c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
        (tx_hash_hex, tx_signed_raw_hex) = c.create(agent_roles['ALICE'], agent_roles['BOB'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)

        queue_create(
                default_chain_spec,
                i,
                agent_roles['ALICE'],
                tx_hash_hex,
                tx_signed_raw_hex,
                session=init_database,
                )
        cache_gas_data(
                tx_hash_hex,
                tx_signed_raw_hex,
                default_chain_spec.asdict(),
                )
        tx_hashes.append(tx_hash_hex)
        txs.append(tx_signed_raw_hex)

    init_database.commit()

    api = AdminApi(eth_rpc, queue=None, call_address=contract_roles['DEFAULT'])
    t = api.fix_nonce(default_chain_spec, agent_roles['ALICE'], 3)
    r = t.get_leaf()
    assert t.successful()

    init_database.commit()
   
    txs = get_nonce_tx_local(default_chain_spec, 3, agent_roles['ALICE'], session=init_database)
    ks = txs.keys()
    assert len(ks) == 2

    for k in ks:
        #hsh = add_0x(k)
        hsh = tx_normalize.tx_hash(k)
        otx = Otx.load(hsh, session=init_database)
        init_database.refresh(otx)
        logg.debug('checking nonce {} tx {} status {}'.format(3, otx.tx_hash, otx.status))
        if add_0x(k) == tx_hashes[3]:
            assert otx.status & StatusBits.OBSOLETE == StatusBits.OBSOLETE
        else:
            assert otx.status == 1
