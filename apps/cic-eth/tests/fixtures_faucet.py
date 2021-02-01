# third-party imports
import pytest
from cic_registry.pytest import *
from erc20_single_shot_faucet import Faucet
from cic_registry import zero_address


@pytest.fixture(scope='session')
def faucet_amount():
    return 50


@pytest.fixture(scope='session')
def faucet(
        faucet_amount,
        config,
        default_chain_spec,
        cic_registry,
        bancor_tokens,
        w3_account_roles,
        w3_account_token_owners,
        solidity_abis,
        w3,
        #accounts_registry,
        ):


    abi = Faucet.abi('storage')
    bytecode = Faucet.bytecode('storage')

    cs = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx_hash = cs.constructor().transact({'from': w3_account_roles['eth_account_faucet_owner']})
    rcpt = w3.eth.getTransactionReceipt(tx_hash)
    cs_address = rcpt.contractAddress
        
    abi = Faucet.abi()
    bytecode = Faucet.bytecode()
    cf = w3.eth.contract(abi=abi, bytecode=bytecode)

    tx_hash = cf.constructor(
        [
            w3_account_roles['eth_account_faucet_owner']
            ],
        bancor_tokens[0],
        cs_address,
        zero_address,
        #accounts_registry,
        ).transact({
            'from': w3_account_roles['eth_account_faucet_owner']
            }
            )

    rcpt = w3.eth.getTransactionReceipt(tx_hash)
    cf_address = rcpt.contractAddress
    
    c = w3.eth.contract(abi=abi, address=cf_address)
    c.functions.setAmount(50).transact({
            'from': w3_account_roles['eth_account_faucet_owner']
        }
        )

    logg.debug('foo {} bar {}'.format(cf_address, w3_account_roles))

    # fund the faucet with token balance
    token = w3.eth.contract(abi=solidity_abis['ERC20'], address=bancor_tokens[0])
    token_symbol = token.functions.symbol().call()
    tx_hash = token.functions.transfer(cf_address, 100000).transact({
        'from': w3_account_token_owners[token_symbol],
        })

    CICRegistry.add_contract(default_chain_spec, c, 'Faucet')

    return cf_address
 
