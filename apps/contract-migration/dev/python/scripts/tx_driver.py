# standard imports
import os
import logging
import argparse
import re
import json
import signal
import random
import time

# third-party imports
import confini
import web3
from cic_registry.chain import ChainSpec
from cic_registry.chain import ChainRegistry
from cic_registry import CICRegistry
from eth_token_index import TokenUniqueSymbolIndex as TokenIndex
from eth_accounts_index import AccountRegistry

from cic_eth.api import Api


logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()
logging.getLogger('websockets.protocol').setLevel(logging.CRITICAL)
logging.getLogger('web3.RequestManager').setLevel(logging.CRITICAL)
logging.getLogger('web3.providers.WebsocketProvider').setLevel(logging.CRITICAL)
logging.getLogger('web3.providers.HTTPProvider').setLevel(logging.CRITICAL)

default_data_dir = '/usr/local/share/cic/solidity/abi'

argparser = argparse.ArgumentParser()
argparser.add_argument('-c', type=str, default='./config', help='config file')
argparser.add_argument('-i', '--chain-spec', dest='i', type=str, help='chain spec')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('--abi-dir', dest='abi_dir', type=str, default=default_data_dir, help='Directory containing bytecode and abi (default: {})'.format(default_data_dir))
argparser.add_argument('-v', action='store_true', help='be verbose')
argparser.add_argument('-vv', action='store_true', help='be more verbose')
argparser.add_argument('--wait-max', dest='wait_max', default=2.0, type=float, help='maximum time in decimal seconds to wait between transactions')
argparser.add_argument('--account-index-address', dest='account_index', type=str, help='Contract address of accounts index')
argparser.add_argument('--token-index-address', dest='token_index', type=str, help='Contract address of token index')
argparser.add_argument('--approval-escrow-address', dest='approval_escrow', type=str, help='Contract address for transfer approvals')
argparser.add_argument('--declarator-address', dest='declarator', type=str, help='Address of declarations contract to perform lookup against')
argparser.add_argument('-a', '--accounts-index-writer', dest='a', type=str, help='Address of account with access to add to accounts index')

args = argparser.parse_args()

if args.vv:
    logging.getLogger().setLevel(logging.DEBUG)
elif args.v:
    logging.getLogger().setLevel(logging.INFO)

config = confini.Config(args.c, args.env_prefix)
config.process()
args_override = {
        'ETH_ABI_DIR': getattr(args, 'abi_dir'),
        'CIC_CHAIN_SPEC': getattr(args, 'i'),
        'DEV_ETH_ACCOUNTS_INDEX_ADDRESS': getattr(args, 'account_index'),
        'DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER': getattr(args, 'a'),
        'DEV_ETH_ERC20_APPROVAL_ESCROW_ADDRESS': getattr(args, 'approval_escrow'),
        'DEV_ETH_TOKEN_INDEX_ADDRESS': getattr(args, 'token_index'),
        }
config.dict_override(args_override, 'cli flag')
config.validate()
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
logg.debug('config:\n{}'.format(config))

re_websocket = r'^wss?:'
re_http = r'^https?:'
blockchain_provider = None
if re.match(re_websocket, config.get('ETH_PROVIDER')):
    blockchain_provider = web3.Web3.WebsocketProvider(config.get('ETH_PROVIDER'))
elif re.match(re_http, config.get('ETH_PROVIDER')):
    blockchain_provider = web3.Web3.HTTPProvider(config.get('ETH_PROVIDER'))
w3 = web3.Web3(blockchain_provider)


chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))
CICRegistry.init(w3, config.get('CIC_REGISTRY_ADDRESS'), chain_spec)
CICRegistry.add_path(config.get('ETH_ABI_DIR'))

chain_registry = ChainRegistry(chain_spec)
CICRegistry.add_chain_registry(chain_registry, True)

run = True

def inthandler(name, frame):
    logg.warning('got {}, stopping'.format(name))
    global run
    run = False

signal.signal(signal.SIGTERM, inthandler)
signal.signal(signal.SIGINT, inthandler)

api = Api(str(chain_spec))

f = open(os.path.join(config.get('ETH_ABI_DIR'), 'ERC20.json'))
erc20_abi = json.load(f)
f.close()

def get_tokens():
    tokens = []
    token_index = TokenIndex(w3, config.get('CIC_TOKEN_INDEX_ADDRESS'))
    token_count = token_index.count()
    for i in range(token_count):
        tokens.append(token_index.get_index(i))
    logg.debug('tokens {}'.format(tokens))
    return tokens

def get_addresses():
    address_index = AccountRegistry(w3, config.get('CIC_ACCOUNTS_INDEX_ADDRESS'))
    address_count = address_index.count()
    addresses = address_index.last(address_count-1)
    logg.debug('addresses {} {}'.format(address_count, addresses))
    return addresses

random.seed()

while run:
    n = random.randint(0, 255)

    # some of the time do other things than transfers
    if n & 0xf8 == 0xf8:
        t = api.create_account()
        logg.info('create account {}'.format(t))
             
    else:
        tokens = get_tokens()
        addresses = get_addresses()
        address_pair = random.choices(addresses, k=2)
        sender = address_pair[0]
        recipient = address_pair[1]
        token = random.choice(tokens)

        c = w3.eth.contract(abi=erc20_abi, address=token)
        sender_balance = c.functions.balanceOf(sender).call()
        token_symbol = c.functions.symbol().call()
        amount = int(random.random() * (sender_balance / 2))

        n = random.randint(0, 255)

        if n & 0xc0 == 0xc0: 
            t = api.transfer_request(sender, recipient, config.get('CIC_APPROVAL_ESCROW_ADDRESS'), amount, token_symbol)
            logg.info('transfer REQUEST {} {} from {} to {} => {}'.format(amount, token_symbol, sender, recipient, t))
        else:
            t = api.transfer(sender, recipient, amount, token_symbol)
            logg.info('transfer {} {} from {} to {} => {}'.format(amount, token_symbol, sender, recipient, t))

    time.sleep(random.random() * args.wait_max)
