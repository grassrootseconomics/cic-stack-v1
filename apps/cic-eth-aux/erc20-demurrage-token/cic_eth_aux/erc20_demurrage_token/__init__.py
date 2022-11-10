# standard imports
import logging

# external imports
import celery
from erc20_demurrage_token.demurrage import DemurrageCalculator
from chainlib.connection import RPCConnection
from chainlib.chain import ChainSpec
from chainlib.eth.constant import ZERO_ADDRESS
from cic_eth_registry import CICRegistry

logg = logging.getLogger(__name__)

celery_app = celery.current_app


class NoopCalculator:

    def amount_since(self, amount, timestamp):
        logg.debug('noopcalculator amount {} timestamp {}'.format(amount, timestamp))
        return amount


class DemurrageCalculationTask(celery.Task):

    demurrage_token_calcs = {}

    @classmethod
    def register_token(cls, rpc, chain_spec, token_symbol, sender_address=ZERO_ADDRESS):
        registry = CICRegistry(chain_spec, rpc)
        token_address = registry.by_name(token_symbol, sender_address=sender_address)
        try:
            c = DemurrageCalculator.from_contract(rpc, chain_spec, token_address, sender_address=sender_address)
            logg.info('found demurrage calculator for ERC20 {} @ {}'.format(token_symbol, token_address))
        except:
            logg.warning('Token {} at address {} does not appear to be a demurrage contract. Calls to balance adjust for this token will always return the same amount'.format(token_symbol, token_address))
            c = NoopCalculator()

        cls.demurrage_token_calcs[token_symbol] = c


@celery_app.task(bind=True, base=DemurrageCalculationTask)
def get_adjusted_balance(self, token_symbol, amount, timestamp):
    c = self.demurrage_token_calcs[token_symbol]
    return c.amount_since(amount, timestamp)


def aux_setup(rpc, config, sender_address=ZERO_ADDRESS):
    chain_spec_str = config.get('CHAIN_SPEC')
    chain_spec = ChainSpec.from_chain_str(chain_spec_str)
    token_symbol = config.get('CIC_DEFAULT_TOKEN_SYMBOL')
    
    DemurrageCalculationTask.register_token(rpc, chain_spec, token_symbol, sender_address=sender_address)
