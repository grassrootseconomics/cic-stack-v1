# standard imports
import logging
import time

# third-party imports
from erc20_approval_escrow import TransferApproval
import celery
import sha3

# local imports
from cic_eth.eth.token import TokenTxFactory

logg = logging.getLogger()


# BUG: transaction receipt only found sometimes
def test_transfer_approval(
    default_chain_spec,
    transfer_approval,
    bancor_tokens,
    w3_account_roles,
    eth_empty_accounts,
    cic_registry,
    init_database,
    celery_session_worker,
    init_eth_tester,
    init_w3,
        ):

    s = celery.signature(
            'cic_eth.eth.request.transfer_approval_request',
            [
                [
                    {
                        'address': bancor_tokens[0],
                        },
                    ],
                w3_account_roles['eth_account_sarafu_owner'],
                eth_empty_accounts[0],
                1024,
                str(default_chain_spec),
                ],
         )

    s_send = celery.signature(
            'cic_eth.eth.tx.send',
            [
                str(default_chain_spec),
                ],
            
            )
    s.link(s_send)
    t = s.apply_async()

    tx_signed_raws = t.get()
    for r in t.collect():
        logg.debug('result {}'.format(r))

    assert t.successful()

    init_eth_tester.mine_block()

    h = sha3.keccak_256()
    tx_signed_raw = tx_signed_raws[0]
    tx_signed_raw_bytes = bytes.fromhex(tx_signed_raw[2:])
    h.update(tx_signed_raw_bytes)
    tx_hash = h.digest()
    rcpt = init_w3.eth.getTransactionReceipt(tx_hash)

    assert rcpt.status == 1

    a = TransferApproval(init_w3, transfer_approval)
    assert a.last_serial() == 1

    logg.debug('requests {}'.format(a.requests(1)['serial']))

