# third-party imports
import celery

# local imports
from cic_eth.admin.nonce import shift_nonce
from cic_eth.queue.tx import create as queue_create
from cic_eth.eth.tx import otx_cache_parse_tx
from cic_eth.eth.task import sign_tx

def test_shift_nonce(
    default_chain_spec,
    init_database,
    init_w3,
    celery_session_worker,
    ):

    chain_str = str(default_chain_spec)

    tx_hashes = []
    for i in range(5):
        tx = {
            'from': init_w3.eth.accounts[0],
            'to': init_w3.eth.accounts[i],
            'nonce': i,
            'gas': 21000,
            'gasPrice': 1000000,
            'value': 128,
            'chainId': default_chain_spec.chain_id(),
            'data': '',
            }
    
        (tx_hash_hex, tx_signed_raw_hex) = sign_tx(tx, chain_str)
        queue_create(tx['nonce'], init_w3.eth.accounts[0], tx_hash_hex, tx_signed_raw_hex, chain_str)
        otx_cache_parse_tx(tx_hash_hex, tx_signed_raw_hex, chain_str)
        tx_hashes.append(tx_hash_hex)

    s = celery.signature(
            'cic_eth.admin.nonce.shift_nonce',
            [
                chain_str,
                tx_hashes[2],
                ],
            queue=None,
                )
    t = s.apply_async()
    r = t.get()
    for _ in t.collect():
        pass
    assert t.successful()
