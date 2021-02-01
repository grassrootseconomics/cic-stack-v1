from cic_eth.eth.util import unpack_signed_raw_tx 
from cic_eth.eth.task import sign_tx

def test_unpack(
    init_rpc,
    w3,
        ):

    tx = {
        'from': w3.eth.accounts[1],
        'to': w3.eth.accounts[0],
        'nonce': 0,
        'value': 1024,
        'gas': 21000,
        'gasPrice': 200000000,
        'data': '0x',
        'chainId': 8995,
            }

    (tx_hash, tx_raw) = sign_tx(tx, 'Foo:8995')

    tx_recovered = unpack_signed_raw_tx(bytes.fromhex(tx_raw[2:]), 8995)

    assert tx_hash == tx_recovered['hash']
