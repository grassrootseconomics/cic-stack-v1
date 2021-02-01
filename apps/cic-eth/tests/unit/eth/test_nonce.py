# standard imports
import logging

# local imports
from cic_eth.eth.nonce import NonceOracle

logg = logging.getLogger()


def test_nonce_sequence(
        eth_empty_accounts,
        init_database,
        init_rpc,
        ):

    account= init_rpc.w3.eth.personal.new_account('')
    no = NonceOracle(account, 0)
    n = no.next()
    assert n == 0

    n = no.next()
    assert n == 1

    init_rpc.w3.eth.sendTransaction({
        'from': init_rpc.w3.eth.accounts[0],
        'to': account,
        'value': 200000000,
        })
    init_rpc.w3.eth.sendTransaction({
        'from': account,
        'to': eth_empty_accounts[0],
        'value': 100,
        })

    c = init_rpc.w3.eth.getTransactionCount(account, 'pending')
    logg.debug('nonce {}'.format(c))

    account= init_rpc.w3.eth.personal.new_account('')
    no = NonceOracle(account, c)

    n = no.next()
    assert n == 1

    n = no.next()
    assert n == 2

    # try with bogus value
    no = NonceOracle(account, 4) 
    n = no.next()
    assert n == 3

