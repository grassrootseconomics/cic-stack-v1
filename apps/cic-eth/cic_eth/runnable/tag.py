# standard imports
import os
import sys
import logging
import argparse
import re

# third-party imports
import web3
from web3 import HTTPProvider, WebsocketProvider
import confini

# local imports
from cic_eth.api import AdminApi
from cic_eth.eth import RpcClient
from cic_eth.db import dsn_from_config
from cic_eth.db.models.base import SessionBase

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

default_config_dir = os.environ.get('CONFINI_DIR', '/usr/local/etc/cic')


argparser = argparse.ArgumentParser(description='daemon that monitors transactions in new blocks')
argparser.add_argument('-p', '--provider', dest='p', type=str, help='Web3 provider url (http only)')
argparser.add_argument('-c', type=str, default=default_config_dir, help='config root to use')
argparser.add_argument('-v', help='be verbose', action='store_true')
argparser.add_argument('-i', '--chain-spec', dest='i', type=str, help='chain spec')
argparser.add_argument('-vv', help='be more verbose', action='store_true')
argparser.add_argument('tag', type=str, help='address tag')
argparser.add_argument('address', type=str, help='address')
args = argparser.parse_args(sys.argv[1:])

if args.v == True:
    logging.getLogger().setLevel(logging.INFO)
elif args.vv == True:
    logging.getLogger().setLevel(logging.DEBUG)

config = confini.Config(args.c)
config.process()
args_override = {
        'ETH_PROVIDER': getattr(args, 'p'),
        'CIC_CHAIN_SPEC': getattr(args, 'i'),
        }
config.dict_override(args_override, 'cli flag')
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
logg.debug('config loaded from {}\n{}'.format(args.c, config))


dsn = dsn_from_config(config)
SessionBase.connect(dsn)

re_websocket = re.compile('^wss?://')
re_http = re.compile('^https?://')
blockchain_provider = config.get('ETH_PROVIDER')
if re.match(re_websocket, blockchain_provider) != None:
    blockchain_provider = WebsocketProvider(blockchain_provider)
elif re.match(re_http, blockchain_provider) != None:
    blockchain_provider = HTTPProvider(blockchain_provider)
else:
    raise ValueError('unknown provider url {}'.format(blockchain_provider))

def web3_constructor():
    w3 = web3.Web3(blockchain_provider)
    return (blockchain_provider, w3)
RpcClient.set_constructor(web3_constructor)
c = RpcClient(config.get('CIC_CHAIN_SPEC'))

def main():
    api = AdminApi(c)
    api.tag_account(args.tag, args.address)


if __name__ == '__main__':
    main()
