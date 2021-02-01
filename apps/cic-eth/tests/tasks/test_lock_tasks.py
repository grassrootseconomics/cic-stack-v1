# standard imports
import os

# third-party imports
import celery
import pytest

# local imports
from cic_eth.db.models.lock import Lock
from cic_eth.db.models.otx import Otx
from cic_eth.db.enum import LockEnum
from cic_eth.error import LockedError


@pytest.mark.parametrize(
        'task_postfix,flag_enum',
        [
            ('send', LockEnum.SEND),
            ('queue', LockEnum.QUEUE),
            ],
        )
def test_lock_task(
    init_database,
    celery_session_worker,
    default_chain_spec,
    task_postfix,
    flag_enum,
    ):

    chain_str = str(default_chain_spec)
    address = '0x' + os.urandom(20).hex()

    s = celery.signature(
            'cic_eth.admin.ctrl.lock_{}'.format(task_postfix),
            [
                'foo',
                chain_str,
                address,
                ],
            )
    t = s.apply_async()
    r = t.get()
    assert t.successful()
    assert r == 'foo'

    q = init_database.query(Lock)
    q = q.filter(Lock.address==address)
    lock = q.first()
    assert lock != None
    assert lock.flags == flag_enum
       
    s = celery.signature(
            'cic_eth.admin.ctrl.unlock_{}'.format(task_postfix),
            [
                'foo',
                chain_str,
                address,
                ],
            )
    t = s.apply_async()
    r = t.get()
    assert t.successful()
    assert r == 'foo'

    q = init_database.query(Lock)
    q = q.filter(Lock.address==address)
    lock = q.first()
    assert lock == None


def test_lock_check_task(
        init_database,
        celery_session_worker,
        default_chain_spec,
        ):

    chain_str = str(default_chain_spec)
    address = '0x' + os.urandom(20).hex()

    s = celery.signature(
            'cic_eth.admin.ctrl.lock_send',
            [
                'foo',
                chain_str,
                address,
                ],
            )
    t = s.apply_async()
    r = t.get()

    s = celery.signature(
            'cic_eth.admin.ctrl.lock_queue',
            [
                'foo',
                chain_str,
                address,
                ],
            )
    t = s.apply_async()
    r = t.get()

    s = celery.signature(
            'cic_eth.admin.ctrl.check_lock',
            [
                'foo',
                chain_str,
                LockEnum.SEND,
                address,
                ],
            )
    t = s.apply_async()

    with pytest.raises(LockedError):
        r = t.get()


    s = celery.signature(
            'cic_eth.admin.ctrl.check_lock',
            [
                'foo',
                chain_str,
                LockEnum.CREATE,
                address,
                ],
            )
    t = s.apply_async()
    r = t.get()
    assert r == 'foo'


def test_lock_arbitrary_task(
    init_database,
    celery_session_worker,
    default_chain_spec,
    ):

    chain_str = str(default_chain_spec)
    address = '0x' + os.urandom(20).hex()

    s = celery.signature(
            'cic_eth.admin.ctrl.lock',
            [
                'foo',
                chain_str,
                address,
                LockEnum.SEND | LockEnum.QUEUE,
                ],
            )
    t = s.apply_async()
    r = t.get()
    assert r == 'foo'

    s = celery.signature(
            'cic_eth.admin.ctrl.check_lock',
            [
                'foo',
                chain_str,
                LockEnum.SEND | LockEnum.QUEUE,
                address,
                ],
            )
    t = s.apply_async()
    with pytest.raises(LockedError):
        r = t.get()
    assert r == 'foo'

    s = celery.signature(
            'cic_eth.admin.ctrl.unlock',
            [
                'foo',
                chain_str,
                address,
                LockEnum.SEND,
                ],
            )
    t = s.apply_async()
    r = t.get()
    assert r == 'foo'


    s = celery.signature(
            'cic_eth.admin.ctrl.check_lock',
            [
                'foo',
                chain_str,
                LockEnum.SEND,
                address,
                ],
            )
    t = s.apply_async()
    r = t.get()


    s = celery.signature(
            'cic_eth.admin.ctrl.unlock',
            [
                'foo',
                chain_str,
                address,
                ],
            )
    t = s.apply_async()
    r = t.get()
    assert r == 'foo'


    s = celery.signature(
            'cic_eth.admin.ctrl.check_lock',
            [
                'foo',
                chain_str,
                LockEnum.QUEUE,
                address,
                ],
            )
    t = s.apply_async()
    r = t.get()


def test_lock_list(
    default_chain_spec,
    init_database,
    celery_session_worker,
    ):

    chain_str = str(default_chain_spec)

    # Empty list of no lock set
    s = celery.signature(
            'cic_eth.queue.tx.get_lock',
            [],
            )
    t = s.apply_async()
    r = t.get()

    assert len(r) == 0 

    # One element if lock set and no link with otx
    tx_hash = '0x' + os.urandom(32).hex()
    address_foo = '0x' + os.urandom(20).hex()
    s = celery.signature(
            'cic_eth.admin.ctrl.lock_send',
            [
                'foo',
                chain_str,
                address_foo,
                tx_hash,
                ],
            )
    t = s.apply_async()
    r = t.get()

    s = celery.signature(
            'cic_eth.queue.tx.get_lock',
            [],
            )
    t = s.apply_async()
    r = t.get()

    assert len(r) == 1
    assert r[0]['tx_hash'] == None
    assert r[0]['address'] == address_foo
    assert r[0]['flags'] == LockEnum.SEND

    # One element if lock set and link with otx, tx_hash now available
    signed_tx = '0x' + os.urandom(128).hex()
    otx = Otx.add(
            0,
            address_foo,
            tx_hash,
            signed_tx,
            )
    s = celery.signature(
            'cic_eth.admin.ctrl.unlock_send',
            [
                'foo',
                chain_str,
                address_foo,
                ],
            )
    t = s.apply_async()
    r = t.get()

    s = celery.signature(
            'cic_eth.admin.ctrl.lock_send',
            [
                'foo',
                chain_str,
                address_foo,
                tx_hash,
                ],
            )
    t = s.apply_async()
    r = t.get()

    s = celery.signature(
            'cic_eth.queue.tx.get_lock',
            [],
            )
    t = s.apply_async()
    r = t.get()

    assert r[0]['tx_hash'] == tx_hash


    # Two elements if two locks in place
    address_bar = '0x' + os.urandom(20).hex()
    tx_hash = '0x' + os.urandom(32).hex()
    s = celery.signature(
            'cic_eth.admin.ctrl.lock_queue',
            [
                'bar',
                chain_str,
                address_bar,
                tx_hash,
                ],
            )
    t = s.apply_async()
    r = t.get()

    s = celery.signature(
            'cic_eth.queue.tx.get_lock',
            [],
            )
    t = s.apply_async()
    r = t.get()

    assert len(r) == 2

    # One element if filtered by address
    s = celery.signature(
            'cic_eth.queue.tx.get_lock',
            [
                address_bar,
                ],
            )
    t = s.apply_async()
    r = t.get()

    assert len(r) == 1
    assert r[0]['tx_hash'] == None
    assert r[0]['address'] == address_bar
    assert r[0]['flags'] == LockEnum.QUEUE

    address_bogus = '0x' + os.urandom(20).hex()
    # No elements if filtered by non-existent address
    s = celery.signature(
            'cic_eth.queue.tx.get_lock',
            [
                address_bogus,
                ],
            )
    t = s.apply_async()
    r = t.get()

