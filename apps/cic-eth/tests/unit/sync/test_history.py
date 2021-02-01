# standard imports
import logging

# third-party imports
import pytest
from web3.exceptions import BlockNotFound
from cic_registry import CICRegistry

# local imports
from cic_eth.sync.history import HistorySyncer
from cic_eth.sync.head import HeadSyncer
#from cic_eth.sync import Syncer
from cic_eth.db.models.otx import OtxSync
from cic_eth.db.models.base import SessionBase
from cic_eth.sync.backend import SyncerBackend

logg = logging.getLogger()

class FinishedError(Exception):
    pass

       
class DebugFilter:

    def __init__(self, address):
        self.txs = []
        self.monitor_to_address = address

    def filter(self, w3, tx, rcpt, chain_spec):
        logg.debug('sync filter {}'.format(tx['hash'].hex()))
        if tx['to'] == self.monitor_to_address:
            self.txs.append(tx)
        # hack workaround, latest block hash not found in eth_tester for some reason
        if len(self.txs) == 2:
            raise FinishedError('intentionally finished on tx {}'.format(tx))


def test_history(
    init_rpc,
    init_database,
    init_eth_tester,
    #celery_session_worker,
    eth_empty_accounts,
        ):

    nonce = init_rpc.w3.eth.getTransactionCount(init_rpc.w3.eth.accounts[0], 'pending') 
    logg.debug('nonce {}'.format(nonce))
    tx = {
        'from': init_rpc.w3.eth.accounts[0],
        'to': eth_empty_accounts[0],
        'value': 404,
        'gas': 21000,
        'gasPrice': init_rpc.w3.eth.gasPrice,
        'nonce': nonce,
            }
    tx_hash_one = init_rpc.w3.eth.sendTransaction(tx)

    nonce = init_rpc.w3.eth.getTransactionCount(init_rpc.w3.eth.accounts[0], 'pending')
    logg.debug('nonce {}'.format(nonce))
    tx = {
        'from': init_rpc.w3.eth.accounts[1],
        'to': eth_empty_accounts[0],
        'value': 404,
        'gas': 21000,
        'gasPrice': init_rpc.w3.eth.gasPrice,
        'nonce': nonce,
            }
    tx_hash_two = init_rpc.w3.eth.sendTransaction(tx)
    init_eth_tester.mine_block()

    block_number = init_rpc.w3.eth.blockNumber

    live_syncer = SyncerBackend.live('foo:666', 0)
    HeadSyncer(live_syncer)

    history_syncers = SyncerBackend.resume('foo:666', block_number)

    for history_syncer in history_syncers:
        logg.info('history syncer start {} target {}'.format(history_syncer.start(), history_syncer.target()))

    backend = history_syncers[0]

    syncer = HistorySyncer(backend)
    fltr = DebugFilter(eth_empty_accounts[0])
    syncer.filter.append(fltr.filter)

    logg.debug('have txs {} {}'.format(tx_hash_one.hex(), tx_hash_two.hex()))

    try:
        syncer.loop(0.1)
    except FinishedError:
        pass
    except BlockNotFound as e:
        logg.error('the last block given in loop does not seem to exist :/ {}'.format(e))

    check_hashes = []
    for h in fltr.txs:
        check_hashes.append(h['hash'].hex())
    assert tx_hash_one.hex() in check_hashes
    assert tx_hash_two.hex() in check_hashes


def test_history_multiple(
    init_rpc,
    init_database,
    init_eth_tester,
    #celery_session_worker,
    eth_empty_accounts,
        ):

    block_number = init_rpc.w3.eth.blockNumber
    live_syncer = SyncerBackend.live('foo:666', block_number)
    HeadSyncer(live_syncer)

    nonce = init_rpc.w3.eth.getTransactionCount(init_rpc.w3.eth.accounts[0], 'pending') 
    logg.debug('nonce {}'.format(nonce))
    tx = {
        'from': init_rpc.w3.eth.accounts[0],
        'to': eth_empty_accounts[0],
        'value': 404,
        'gas': 21000,
        'gasPrice': init_rpc.w3.eth.gasPrice,
        'nonce': nonce,
            }
    tx_hash_one = init_rpc.w3.eth.sendTransaction(tx)


    init_eth_tester.mine_block()
    block_number = init_rpc.w3.eth.blockNumber
    history_syncers = SyncerBackend.resume('foo:666', block_number)
    for history_syncer in history_syncers:
        logg.info('halfway history syncer start {} target {}'.format(history_syncer.start(), history_syncer.target()))
    live_syncer = SyncerBackend.live('foo:666', block_number)
    HeadSyncer(live_syncer)

    nonce = init_rpc.w3.eth.getTransactionCount(init_rpc.w3.eth.accounts[0], 'pending')
    logg.debug('nonce {}'.format(nonce))
    tx = {
        'from': init_rpc.w3.eth.accounts[1],
        'to': eth_empty_accounts[0],
        'value': 404,
        'gas': 21000,
        'gasPrice': init_rpc.w3.eth.gasPrice,
        'nonce': nonce,
            }
    tx_hash_two = init_rpc.w3.eth.sendTransaction(tx)

    init_eth_tester.mine_block()
    block_number = init_rpc.w3.eth.blockNumber
    history_syncers = SyncerBackend.resume('foo:666', block_number)
    live_syncer = SyncerBackend.live('foo:666', block_number)
    HeadSyncer(live_syncer)

    for history_syncer in history_syncers:
        logg.info('history syncer start {} target {}'.format(history_syncer.start(), history_syncer.target()))

    assert len(history_syncers) == 2

    backend = history_syncers[0]
    syncer = HistorySyncer(backend)
    fltr = DebugFilter(eth_empty_accounts[0])
    syncer.filter.append(fltr.filter)
    try:
        syncer.loop(0.1)
    except FinishedError:
        pass
    except BlockNotFound as e:
        logg.error('the last block given in loop does not seem to exist :/ {}'.format(e))

    check_hashes = []
    for h in fltr.txs:
        check_hashes.append(h['hash'].hex())
    assert tx_hash_one.hex() in check_hashes


    backend = history_syncers[1]
    syncer = HistorySyncer(backend)
    fltr = DebugFilter(eth_empty_accounts[0])
    syncer.filter.append(fltr.filter)
    try:
        syncer.loop(0.1)
    except FinishedError:
        pass
    except BlockNotFound as e:
        logg.error('the last block given in loop does not seem to exist :/ {}'.format(e))

    check_hashes = []
    for h in fltr.txs:
        check_hashes.append(h['hash'].hex())
    assert tx_hash_two.hex() in check_hashes

    history_syncers = SyncerBackend.resume('foo:666', block_number)

    assert len(history_syncers) == 0
