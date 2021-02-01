# third-party imports
import pytest
from cic_registry import CICRegistry


@pytest.fixture(scope='session')
def token_registry(
        default_chain_spec,
        cic_registry,
        solidity_abis,
        evm_bytecodes,
        w3,
        ):

    abi = solidity_abis['TokenRegistry']
    bytecode = evm_bytecodes['TokenRegistry']

    c = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx_hash = c.constructor().transact({'from': w3.eth.accounts[0]})
    rcpt = w3.eth.getTransactionReceipt(tx_hash)
    address = rcpt.contractAddress

    c = w3.eth.contract(abi=abi, address=address)

    CICRegistry.add_contract(default_chain_spec, c, 'TokenRegistry')

    return address
