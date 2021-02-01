# third-party imports
import pytest
from cic_registry.pytest import *
from erc20_approval_escrow import TransferApproval


@pytest.fixture(scope='session')
def transfer_approval(
    config,
    default_chain_spec,
    default_chain_registry,
    bancor_tokens,
    w3_account_roles,
    cic_registry,
    w3,
        ):

    abi = TransferApproval.abi()
    bytecode = TransferApproval.bytecode()

    c = w3.eth.contract(abi=abi, bytecode=bytecode)
    approvers = [w3_account_roles['eth_account_approval_owner']]
    tx_hash = c.constructor(approvers).transact({'from': w3_account_roles['eth_account_approval_owner']})
    rcpt = w3.eth.getTransactionReceipt(tx_hash)

    c = w3.eth.contract(abi=abi, address=rcpt.contractAddress)

    CICRegistry.add_contract(default_chain_spec, c, 'TransferApproval')

    return rcpt.contractAddress
