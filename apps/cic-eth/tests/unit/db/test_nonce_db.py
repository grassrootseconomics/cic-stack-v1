# third-party imports
import pytest

# local imports
from cic_eth.db.models.nonce import Nonce

def test_nonce_increment(
        init_database,
        eth_empty_accounts,
        database_engine,
        ):

#    if database_engine[:6] == 'sqlite':
#        pytest.skip('sqlite cannot lock tables which is required for this test, skipping')

    nonce = Nonce.next(eth_empty_accounts[0], 3)
    assert nonce == 3

    nonce = Nonce.next(eth_empty_accounts[0], 3)
    assert nonce == 4
