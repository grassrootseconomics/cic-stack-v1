# standard imports
import logging
import time

# external imports
import celery
import pytest
from chainlib.connection import RPCConnection
from chainlib.eth.nonce import (
        OverrideNonceOracle,
        RPCNonceOracle,
        )
from chainlib.eth.gas import (
        OverrideGasOracle,
        Gas,
        )
from chainlib.eth.tx import (
        unpack,
        TxFormat,
        )
from chainlib.eth.constant import (
        MINIMUM_FEE_UNITS,
        MINIMUM_FEE_PRICE,
        )
from chainqueue.sql.query import get_tx
from chainqueue.db.enum import StatusBits
from chainqueue.sql.state import (
        set_ready,
        set_reserved,
        set_sent,
        )
from chainqueue.db.models.otx import Otx
from hexathon import strip_0x

# local imports
from cic_eth.eth.gas import (
        cache_gas_data,
        MAX_RESEND_ATTEMPTS,
        )
from cic_eth.error import (
        OutOfGasError,
        ResendImpossibleError,
        )
from cic_eth.queue.tx import queue_create
from cic_eth.task import BaseTask
from cic_eth.db.models.base import SessionBase
from cic_eth.db.models.debug import Debug

logg = logging.getLogger()


def test_task_gas_limit(
        eth_rpc,
        eth_signer,
        default_chain_spec,
        agent_roles,
        celery_session_worker,
        ):
    rpc = RPCConnection.connect(default_chain_spec, 'default')
    gas_oracle = BaseTask().create_gas_oracle(rpc)
    c = Gas(default_chain_spec, signer=eth_signer, gas_oracle=gas_oracle)
    (tx_hash_hex, o) = c.create(agent_roles['ALICE'], agent_roles['BOB'], 10, tx_format=TxFormat.RLP_SIGNED)
    tx = unpack(bytes.fromhex(strip_0x(o)), default_chain_spec)
    assert (tx['gas'], BaseTask.min_fee_price)


def test_task_check_gas_ok(
        default_chain_spec,
        eth_rpc,
        eth_signer,
        init_database,
        agent_roles,
        custodial_roles,
        celery_session_worker,
        ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = RPCNonceOracle(agent_roles['ALICE'], conn=eth_rpc) 
    gas_oracle = OverrideGasOracle(price=1000000000, limit=21000)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, tx_signed_raw_hex) = c.create(agent_roles['ALICE'], agent_roles['BOB'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)

    queue_create(
            default_chain_spec,
            0,
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

    init_database.commit()

    s = celery.signature(
            'cic_eth.eth.gas.check_gas',
            [
                [
                    strip_0x(tx_hash_hex),
                    ],
                default_chain_spec.asdict(),
                [],
                None,
                8000000,
                ],
            queue=None
            )
    t = s.apply_async()
    t.get_leaf()
    assert t.successful()

    init_database.commit()

    tx = get_tx(default_chain_spec, tx_hash_hex, session=init_database)
    assert tx['status'] & StatusBits.QUEUED == StatusBits.QUEUED


def test_task_check_gas_insufficient(
        default_chain_spec,
        eth_rpc,
        eth_signer,
        init_database,
        agent_roles,
        custodial_roles,
        celery_session_worker,
        whoever,
        ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = OverrideNonceOracle(whoever, 42)
    gas_oracle = OverrideGasOracle(price=1000000000, limit=21000)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, tx_signed_raw_hex) = c.create(whoever, agent_roles['BOB'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)

    queue_create(
            default_chain_spec,
            42,
            whoever,
            tx_hash_hex,
            tx_signed_raw_hex,
            session=init_database,
            )
    cache_gas_data(
            tx_hash_hex,
            tx_signed_raw_hex,
            default_chain_spec.asdict(),
            )

    init_database.commit()

    s = celery.signature(
            'cic_eth.eth.gas.check_gas',
            [
                [
                    tx_hash_hex,
                    ],
                default_chain_spec.asdict(),
                [],
                None,
                None,
                ],
            queue=None
            )
    t = s.apply_async()
    try:
        r = t.get_leaf()
    except OutOfGasError:
        pass

    init_database.commit()

    tx = get_tx(default_chain_spec, tx_hash_hex, session=init_database)
    assert tx['status'] & StatusBits.GAS_ISSUES == StatusBits.GAS_ISSUES


def test_task_check_gas_low(
        default_chain_spec,
        eth_rpc,
        eth_signer,
        init_database,
        agent_roles,
        custodial_roles,
        celery_session_worker,
        whoever,
        ):

    gas_oracle = OverrideGasOracle(price=MINIMUM_FEE_PRICE, limit=MINIMUM_FEE_UNITS)
    nonce_oracle = RPCNonceOracle(custodial_roles['GAS_GIFTER'], conn=eth_rpc)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, o) = c.create(custodial_roles['GAS_GIFTER'], whoever, 100 * (10 ** 6))
    r = eth_rpc.do(o)

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = RPCNonceOracle(whoever, conn=eth_rpc) 
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, tx_signed_raw_hex) = c.create(whoever, agent_roles['BOB'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)

    queue_create(
            default_chain_spec,
            0,
            whoever,
            tx_hash_hex,
            tx_signed_raw_hex,
            session=init_database,
            )
    cache_gas_data(
            tx_hash_hex,
            tx_signed_raw_hex,
            default_chain_spec.asdict(),
            )

    init_database.commit()

    s = celery.signature(
            'cic_eth.eth.gas.check_gas',
            [
                [
                    tx_hash_hex,
                    ],
                default_chain_spec.asdict(),
                ],
                [],
                None,
                None,
            queue=None
            )
    t = s.apply_async()
    t.get_leaf()
    assert t.successful()

    init_database.commit()

    tx = get_tx(default_chain_spec, tx_hash_hex, session=init_database)
    assert tx['status'] & StatusBits.QUEUED == StatusBits.QUEUED


@pytest.mark.parametrize(
        '_gas_price,_gas_factor,_gas_price_current',
        [
        (None, 1.1, 1000000000),
        (MINIMUM_FEE_PRICE * 1.1, 0.9, 1000000000),
        (1, 1.1, 1),
        (None, 1.3, 1000000000),
        ]
        )
def test_task_resend_explicit(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        agent_roles,
        custodial_roles,
        celery_session_worker,
        _gas_price,
        _gas_factor,
        _gas_price_current,
        ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = RPCNonceOracle(agent_roles['ALICE'], conn=eth_rpc) 
    gas_oracle = OverrideGasOracle(price=_gas_price_current, limit=21000)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, tx_signed_raw_hex) = c.create(agent_roles['ALICE'], agent_roles['BOB'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)

    queue_create(
            default_chain_spec,
            0,
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
    tx_before = unpack(bytes.fromhex(strip_0x(tx_signed_raw_hex)), default_chain_spec)

    init_database.commit()

    set_ready(default_chain_spec, tx_hash_hex, session=init_database)
    set_reserved(default_chain_spec, tx_hash_hex, session=init_database)
    set_sent(default_chain_spec, tx_hash_hex, session=init_database)

    s = celery.signature(
            'cic_eth.eth.gas.resend_with_higher_gas',
            [
                tx_hash_hex,
                default_chain_spec.asdict(),
                _gas_price,
                _gas_factor,
                ],
            queue=None
            )
    t = s.apply_async()
    r = t.get_leaf()
    assert t.successful()

    q = init_database.query(Otx)
    q = q.filter(Otx.tx_hash==strip_0x(r))
    otx = q.first()
    if otx == None:
        raise NotLocalTxError(r)

    tx_after = unpack(bytes.fromhex(strip_0x(otx.signed_tx)), default_chain_spec)
    logg.debug('gasprices before {} after {}'.format(tx_before['gasPrice'], tx_after['gasPrice']))
    assert tx_after['gasPrice'] > tx_before['gasPrice']


def test_retry_impossible(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        agent_roles,
        custodial_roles,
        celery_session_worker,
        ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')

    gas_price = 1
    tx_hashes = []
    for i in range(MAX_RESEND_ATTEMPTS + 2):
        nonce_oracle = OverrideNonceOracle(agent_roles['ALICE'], 0)
        gas_oracle = OverrideGasOracle(price=gas_price, limit=21000)
        c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
        (tx_hash_hex, tx_signed_raw_hex) = c.create(agent_roles['ALICE'], agent_roles['BOB'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)
        tx_hashes.append(tx_hash_hex)

        queue_create(
                default_chain_spec,
                0,
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
        gas_price *= 2

    init_database.commit()

    tx_hash_hex = tx_hashes[0]

    # manually revert state of original transaction back to queued
    q = init_database.query(Otx)
    q = q.filter(Otx.tx_hash==strip_0x(tx_hash_hex))
    otx = q.first()
    otx.status = 1
    init_database.add(otx)
    init_database.commit()

    set_ready(default_chain_spec, tx_hash_hex, session=init_database)
    set_reserved(default_chain_spec, tx_hash_hex, session=init_database)
    set_sent(default_chain_spec, tx_hash_hex, session=init_database)

    s = celery.signature(
            'cic_eth.eth.gas.resend_with_higher_gas',
            [
                tx_hash_hex,
                default_chain_spec.asdict(),
                ],
            queue=None
            )
    t = s.apply_async()

    with pytest.raises(ResendImpossibleError):
        t.get_leaf()

    session = SessionBase.create_session()
    q = session.query(Otx)
    q = q.filter(Otx.tx_hash==strip_0x(tx_hash_hex))
    otx = q.first()
    session.close()

    assert otx.status & StatusBits.UNKNOWN_ERROR.value > 0

    q = init_database.query(Debug)
    r = q.all()
    assert len(r) == 1


