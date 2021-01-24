#!/usr/bin/python

import csv
import logging
import argparse
import os
import re

import web3
import confini

from cic_registry import CICRegistry
from cic_eth.api import Api

logging.basicConfig(level=logging.INFO)
logg = logging.getLogger()

confini_default_dir = os.environ.get('CONFINI_DIR', '/usr/local/etc/cic')


argparser = argparse.ArgumentParser()
argparser.add_argument('-c', type=str, default=confini_default_dir, help='config data dir')
argparser.add_argument('-a', '--token-gifter-address', dest='a', type=str, help='Token gifter address')
argparser.add_argument('-i', '--chain-spec', dest='i', type=str, help='chain spec')
argparser.add_argument('-s', '--token-symbol', dest='s', type=str, help='Token symbol')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('-v', action='store_true', help='be verbose')
argparser.add_argument('-vv', action='store_true', help='be more verbose')
args = argparser.parse_args()

if args.vv:
    logging.getLogger().setLevel(logging.DEBUG)
elif args.v:
    logging.getLogger().setLevel(logging.INFO)

config = confini.Config(args.c, args.env_prefix)
config.process()
args_override = {
        'CIC_CHAIN_SPEC': getattr(args, 'i'),
        }
cic_eth_api = Api(config.get('CIC_CHAIN_SPEC'))

token_gifter_address = args.a

if __name__ == '__main__':
    f = open('./data/amounts', 'r')
    cr = csv.reader(f)
    for r in cr:
        logg.info('sending {} {} from {} to {}'.format(r[1], args.s, token_gifter_address, r[0]))
        cic_eth_api.transfer(token_gifter_address, r[0], int(r[1]), args.s)
    f.close()
