# standard imports
import logging

# third-party imports
import celery
from chainlib.eth.address import to_checksum_address
from hexathon import (
        add_0x,
        strip_0x,
        )

# local imports
from .base import SyncFilter

logg = logging.getLogger().getChild(__name__)

account_registry_add_log_hash = '0x9cc987676e7d63379f176ea50df0ae8d2d9d1141d1231d4ce15b5965f73c9430'


class RegistrationFilter(SyncFilter):

    def __init__(self, chain_spec, queue):
        self.chain_spec = chain_spec
        self.queue = queue


    def filter(self, conn, block, tx, db_session=None): 
        registered_address = None
        for l in tx.logs:
            event_topic_hex = l['topics'][0]
            if event_topic_hex == account_registry_add_log_hash:
                # TODO: use abi conversion method instead

                address_hex = strip_0x(l['topics'][1])[64-40:]
                address = to_checksum_address(add_0x(address_hex))
                logg.info('request token gift to {}'.format(address))
                s_nonce = celery.signature(
                    'cic_eth.eth.nonce.reserve_nonce',
                    [
                        address,
                        self.chain_spec.asdict(),
                        ],
                    queue=self.queue,
                    )
                s_gift = celery.signature(
                    'cic_eth.eth.account.gift',
                    [
                        self.chain_spec.asdict(),
                        ],
                    queue=self.queue,
                    )
                s_nonce.link(s_gift)
                t = s_nonce.apply_async()
                return t


    def __str__(self):
        return 'cic-eth account registration'

