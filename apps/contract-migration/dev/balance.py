#!python3

"""Gas transfer script

.. moduleauthor:: Louis Holbrook <dev@holbrook.no>
.. pgp:: 0826EDA1702D1E87C6E2875121D2E7BB88C2A746 

"""

# SPDX-License-Identifier: GPL-3.0-or-later

# standard imports
import os
import json
import argparse
import logging

# third-party imports
import web3

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

logging.getLogger('web3').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

default_abi_dir = os.environ.get('ETH_ABI_DIR', '/usr/share/local/cic/solidity/abi')
default_eth_provider = os.environ.get('ETH_PROVIDER', 'http://localhost:8545')

argparser = argparse.ArgumentParser()
argparser.add_argument('-p', '--provider', dest='p', default=default_eth_provider, type=str, help='Web3 provider url (http only)')
argparser.add_argument('-t', '--token-address', dest='t', type=str, help='Token address. If not set, will return gas balance')
argparser.add_argument('--abi-dir', dest='abi_dir', type=str, default=default_abi_dir, help='Directory containing bytecode and abi (default {})'.format(default_abi_dir))
argparser.add_argument('-v', action='store_true', help='Be verbose')
argparser.add_argument('account', type=str, help='Account address')
args = argparser.parse_args()


if args.v:
    logg.setLevel(logging.DEBUG)

def main():
    w3 = web3.Web3(web3.Web3.HTTPProvider(args.p))

    balance = None
    if args.t != None:
        f = open(os.path.join(args.abi_dir, 'ERC20.json'))
        abi = json.load(f)
        f.close()
        c = w3.eth.contract(abi=abi, address=args.t)
        balance = c.functions.balanceOf(args.account).call()
    else:
        balance =w3.eth.getBalance(args.account)

    print(balance)

if __name__ == '__main__':
    main()
