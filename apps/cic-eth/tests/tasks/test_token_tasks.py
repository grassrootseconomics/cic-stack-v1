# standard imports
import logging

# third-party imports
import celery

# local imports
from cic_eth.eth.token import TokenTxFactory


logg = logging.getLogger()


def test_approve(
        init_rpc,
        default_chain_spec,
        celery_session_worker,
        bancor_tokens,
        bancor_registry,
        cic_registry,
        ):

    s = celery.signature(
            'cic_eth.eth.token.approve',
            [
                [
                    {
                        'address': bancor_tokens[0],
                    },
                    ],
                init_rpc.w3.eth.accounts[0],
                init_rpc.w3.eth.accounts[1],
                1024,
                str(default_chain_spec),
                ],
            )
    t = s.apply_async()
    t.get()
    for r in t.collect():
        logg.debug('result {}'.format(r))

    assert t.successful()
