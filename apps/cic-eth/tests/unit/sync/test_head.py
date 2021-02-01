# standard imports
import logging

# local imports
from cic_eth.sync.head import HeadSyncer
from cic_eth.sync.backend import SyncerBackend

logg = logging.getLogger()


def test_head(
    init_rpc,
    init_database,
    init_eth_tester,
    mocker,
    eth_empty_accounts,
        ):

    #backend = SyncBackend(eth_empty_accounts[0], 'foo')
    block_number = init_rpc.w3.eth.blockNumber
    backend = SyncerBackend.live('foo:666', block_number)
    syncer = HeadSyncer(backend)

    #init_eth_tester.mine_block()
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

    block_number = init_rpc.w3.eth.blockNumber
    backend.set(block_number, 0)
    b = syncer.get(init_rpc.w3)

    tx = init_rpc.w3.eth.getTransactionByBlock(b[0], 0)

    assert tx.hash.hex() == tx_hash_one.hex()
