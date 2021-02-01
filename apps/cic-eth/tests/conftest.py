# standard imports
import os
import logging
import sys

# third-party imports
import pytest
from cic_registry import CICRegistry

script_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.insert(0, root_dir)
data_dir = os.path.join(script_dir, 'testdata', 'abi')
CICRegistry.add_path(data_dir)

# fixtures
from tests.fixtures_registry import *
from cic_registry.pytest import *
from cic_bancor.pytest import *
from tests.fixtures_config import *
from tests.fixtures_celery import *
from tests.fixtures_web3 import *
from tests.fixtures_database import *
from tests.fixtures_faucet import *
from tests.fixtures_transferapproval import *
from tests.fixtures_account import *

logg = logging.getLogger()


@pytest.fixture(scope='session')
def init_registry(
        init_w3_conn,
        ):
    return CICRegistry


@pytest.fixture(scope='function')
def eth_empty_accounts(
        init_wallet_extension,
        ):
    a = []
    for i in range(10):
        address = init_wallet_extension.new_account()
        a.append(address)
        logg.info('added address {}'.format(a))
    return a
