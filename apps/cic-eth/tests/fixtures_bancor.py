# standard imports
import os
import logging
import json

# third-party imports
import pytest
from cic_registry.bancor import contract_ids
from cic_registry import bancor

# local imports
from cic_eth.eth import rpc

script_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.dirname(script_dir)

logg = logging.getLogger(__file__)


class BancorContractLoader:

    bancor_path = os.path.join(root_dir, 'bancor')
    registry_contract = None

    @staticmethod
    def build_path():
        return BancorContractLoader.bancor_path
#        return os.path.join(BancorContractLoader.bancor_path, 'solidity', 'build', 'contracts')


    @staticmethod
    def contract(w3, bundle_id, registry_id=None):
        if registry_id == None:
            registry_id = bundle_id
        contract_id_hex = w3.toHex(text=registry_id)
        contract_address = BancorContractLoader.registry_contract.functions.addressOf(contract_id_hex).call()
        contract_build_file = os.path.join(
                BancorContractLoader.build_path(),
                '{}.json'.format(bundle_id),
                )
        f = open(os.path.join(contract_build_file))
        j = json.load(f)
        f.close()
        contract_abi = j['abi']
        logg.debug('creating contract interface {} ({}) at address {}'.format(registry_id, bundle_id, contract_address))
        contract = w3.eth.contract(abi=contract_abi, address=contract_address)
        return contract



# TODO: DRY
@pytest.fixture(scope='session')
def bancor_deploy(
        load_config,
        init_w3_conn,
        ):
    bancor_dir_default = os.path.join(root_dir, 'bancor')
    logg.debug('bancor deploy "{}"'.format(bancor_dir_default))
    BancorContractLoader.bancor_path = load_config.get('BANCOR_DIR', bancor_dir_default)
    bancor_build_dir = BancorContractLoader.build_path()

    # deploy registry
    registry_build_file = os.path.join(bancor_build_dir, 'ContractRegistry.json')
    f = open(os.path.join(registry_build_file))
    j = json.load(f)
    f.close()
    registry_constructor = init_w3_conn.eth.contract(abi=j['abi'], bytecode=j['bytecode'])
    tx = registry_constructor.constructor().transact()
    rcpt = init_w3_conn.eth.getTransactionReceipt(tx)
    registry_address = rcpt['contractAddress']
    registry_contract = init_w3_conn.eth.contract(abi=j['abi'], address=registry_address)
    BancorContractLoader.registry_contract = registry_contract

    # deply reserve token
    reservetoken_build_file = os.path.join(bancor_build_dir, 'EtherToken.json')
    f = open(os.path.join(reservetoken_build_file))
    j = json.load(f)
    f.close()
    reservetoken_constructor = init_w3_conn.eth.contract(abi=j['abi'], bytecode=j['bytecode'])
    tx = reservetoken_constructor.constructor('Reserve', 'RSV').transact()
    rcpt = init_w3_conn.eth.getTransactionReceipt(tx)
    reservetoken_address = rcpt['contractAddress']
    reservetoken_contract = init_w3_conn.eth.contract(abi=j['abi'], address=reservetoken_address)

    # register reserve token as bancor hub token
    key_hex = init_w3_conn.toHex(text='BNTToken')
    registry_contract.functions.registerAddress(key_hex, reservetoken_address).transact()

    # deposit balances for minting liquid tokens with reserve
    init_w3_conn.eth.sendTransaction({
        'from': init_w3_conn.eth.accounts[1],
        'to': reservetoken_address,
        'value': init_w3_conn.toWei('101', 'ether'),
        'nonce': 0,
        })
    init_w3_conn.eth.sendTransaction({
        'from': init_w3_conn.eth.accounts[2],
        'to': reservetoken_address,
        'value': init_w3_conn.toWei('101', 'ether'),
        'nonce': 0,
        })

    # deploy converter factory contract for creating liquid token exchanges
    build_file = os.path.join(bancor_build_dir, 'LiquidTokenConverterFactory.json')
    f = open(build_file)
    j = json.load(f)
    f.close()
    converterfactory_constructor = init_w3_conn.eth.contract(abi=j['abi'], bytecode=j['bytecode'])
    tx = converterfactory_constructor.constructor().transact()
    rcpt = init_w3_conn.eth.getTransactionReceipt(tx)
    converter_factory_address = rcpt['contractAddress']

    # deploy the remaining contracts managed by the registry
    for k in contract_ids.keys():
        build_file = os.path.join(bancor_build_dir, '{}.json'.format(k))
        f = open(build_file)
        j = json.load(f)
        f.close()
        contract_constructor = init_w3_conn.eth.contract(abi=j['abi'], bytecode=j['bytecode'])
        tx = None

        # include the registry address as constructor parameters for the contracts that require it
        if k in ['ConverterRegistry', 'ConverterRegistryData', 'BancorNetwork', 'ConversionPathFinder']:
            tx = contract_constructor.constructor(registry_address).transact()
        else:
            tx = contract_constructor.constructor().transact()
        rcpt = init_w3_conn.eth.getTransactionReceipt(tx)
        contract_address = rcpt['contractAddress']

        # register contract in registry
        key_hex = init_w3_conn.toHex(text=contract_ids[k])
        registry_contract.functions.registerAddress(key_hex, contract_address).transact()
        contract = init_w3_conn.eth.contract(abi=j['abi'], address=contract_address)

        # bancor formula needs to be initialized before use
        if k == 'BancorFormula':
            logg.debug('init bancor formula {}'.format(contract_address))
            contract.functions.init().transact()

        # converter factory needs liquid token converter factory to be able to issue our liquid tokens
        if k == 'ConverterFactory':
            logg.debug('register converter factory {}'.format(converter_factory_address))
            contract.functions.registerTypedConverterFactory(converter_factory_address).transact()
    
    logg.info('deployed registry at address {}'.format(registry_address))
    return registry_contract



def __create_converter(w3, converterregistry_contract, reserve_address, owner_address, token_name, token_symbol):
    converterregistry_contract.functions.newConverter(
            0, 
            token_name,
            token_symbol,
            18,
            100000,
            [reserve_address],
            [250000],
            ).transact({
                'from': owner_address,
                })


@pytest.fixture(scope='session')
def tokens_to_deploy(
        ):
    return [
        (1, 'Bert Token', 'BRT'), # account_index, token name, token symbol
        (2, 'Ernie Token', 'RNI'),
            ]


@pytest.fixture(scope='session')
def bancor_tokens(
    init_w3_conn,
    bancor_deploy,
    tokens_to_deploy,
    ):

    registry_contract = bancor_deploy

    reserve_contract = BancorContractLoader.contract(init_w3_conn, 'ERC20Token', 'BNTToken')
    reserve_address = reserve_contract.address

    network_id = init_w3_conn.toHex(text='BancorNetwork')
    network_address = registry_contract.functions.addressOf(network_id).call()

    converterregistry_contract = BancorContractLoader.contract(init_w3_conn, 'ConverterRegistry', 'BancorConverterRegistry')

    for p in tokens_to_deploy:
        __create_converter(init_w3_conn, converterregistry_contract, reserve_address, init_w3_conn.eth.accounts[p[0]], p[1], p[2])

    tokens = converterregistry_contract.functions.getAnchors().call()

    network_contract = BancorContractLoader.contract(init_w3_conn, 'BancorNetwork')

    mint_amount = init_w3_conn.toWei('100', 'ether')
    i = 0
    for token in tokens:
        i += 1
        owner = init_w3_conn.eth.accounts[i]
        logg.debug('owner {} is {}'.format(owner, token))
        reserve_contract.functions.approve(network_address, 0).transact({
            'from': owner
            })
        reserve_contract.functions.approve(network_address, mint_amount).transact({
            'from': owner
            })
        logg.debug('convert {} {} {} {}'.format(reserve_address, token, mint_amount, owner))
        network_contract.functions.convert([
            reserve_address,
            token,
            token,
            ],
            mint_amount,
            mint_amount,
            ).transact({
                'from': owner,
                })
    
    return tokens


@pytest.fixture(scope='session')
def bancor_load(
        load_config,
        init_w3_conn,
        bancor_deploy,
        bancor_tokens,
        ):
    registry_address = bancor_deploy.address
    bancor_dir_default = os.path.join(root_dir, 'bancor')
    bancor_dir = load_config.get('BANCOR_DIR', bancor_dir_default)
    bancor.load(init_w3_conn, registry_address, bancor_dir)
