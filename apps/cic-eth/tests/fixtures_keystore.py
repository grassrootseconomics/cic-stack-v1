# standard imports
import os
import json
import logging

# third-party imports
import pytest
from cic_eth.eth.rpc import RpcClient
from crypto_dev_signer.keystore import ReferenceKeystore
#from crypto_dev_signer.eth.web3ext import Web3 as Web3ext

logg = logging.getLogger(__file__)


# TODO: need mock for deterministic signatures
# depends on mock blockchain (ganache) where private key is passed directly to this module
@pytest.fixture(scope='session')
def init_mock_keystore(
        ):
    raise NotImplementedError


@pytest.fixture(scope='session')
def init_keystore(
        load_config,
        database_engine,
        ):
        #symkey_hex = os.environ.get('CIC_SIGNER_SECRET')
        symkey_hex = load_config.get('SIGNER_SECRET')
        symkey = bytes.fromhex(symkey_hex)
        opt = {
                'symmetric_key': symkey,
                }
        k = ReferenceKeystore(database_engine, **opt)
        k.db_session.execute('DELETE from ethereum')
        k.db_session.commit()
        keys_file = load_config.get('SIGNER_DEV_KEYS_PATH')
        addresses = []
        if keys_file:
            logg.debug('loading keys from {}'.format(keys_file))
            f = open(keys_file, 'r')
            j = json.load(f)
            f.close()
            signer_password = load_config.get('SIGNER_PASSWORD')
            for pk in j['private']:
                address_hex = k.import_raw_key(bytes.fromhex(pk[2:]), signer_password)
                addresses.append(address_hex)
    
        RpcClient.set_provider_address(addresses[0])
        return addresses


