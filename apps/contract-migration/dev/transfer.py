#!python3

"""Token transfer script

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
from crypto_dev_signer.eth.signer import ReferenceSigner as EIP155Signer
from crypto_dev_signer.keystore import DictKeystore
from crypto_dev_signer.eth.helper import EthTxExecutor

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

logging.getLogger('web3').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

default_abi_dir = '/usr/share/local/cic/solidity/abi'
argparser = argparse.ArgumentParser()
argparser.add_argument('-p', '--provider', dest='p', default='http://localhost:8545', type=str, help='Web3 provider url (http only)')
argparser.add_argument('-w', action='store_true', help='Wait for the last transaction to be confirmed')
argparser.add_argument('-ww', action='store_true', help='Wait for every transaction to be confirmed')
argparser.add_argument('-i', '--chain-spec', dest='i', type=str, default='Ethereum:1', help='Chain specification string')
argparser.add_argument('--token-address', required='True', dest='t', type=str, help='Token address')
argparser.add_argument('-a', '--sender-address', dest='s', type=str, help='Sender account address')
argparser.add_argument('-y', '--key-file', dest='y', type=str, help='Ethereum keystore file to use for signing')
argparser.add_argument('--abi-dir', dest='abi_dir', type=str, default=default_abi_dir, help='Directory containing bytecode and abi (default {})'.format(default_abi_dir))
argparser.add_argument('-v', action='store_true', help='Be verbose')
argparser.add_argument('-vv', action='store_true', help='Be more verbose')
argparser.add_argument('recipient', type=str, help='Recipient account address')
argparser.add_argument('amount', type=int, help='Amount of tokens to mint and gift')
args = argparser.parse_args()


if args.vv:
    logg.setLevel(logging.DEBUG)
elif args.v:
    logg.setLevel(logging.INFO)

block_last = args.w
block_all = args.ww

w3 = web3.Web3(web3.Web3.HTTPProvider(args.p))

signer_address = None
keystore = DictKeystore()
if args.y != None:
    logg.debug('loading keystore file {}'.format(args.y))
    signer_address = keystore.import_keystore_file(args.y)
    logg.debug('now have key for signer address {}'.format(signer_address))
signer = EIP155Signer(keystore)

chain_pair = args.i.split(':')
chain_id = int(chain_pair[1])

helper = EthTxExecutor(
        w3,
        signer_address,
        signer,
        chain_id,
        block=args.ww,
    )


def main():
    # TODO: Add pure ERC20 abi to collection
    f = open(os.path.join(args.abi_dir, 'ERC20.json'), 'r')
    abi = json.load(f)
    f.close()

    c = w3.eth.contract(abi=abi, address=args.t)

    recipient = args.recipient
    value = args.amount

    logg.debug('sender {} balance before: {}'.format(signer_address, c.functions.balanceOf(signer_address).call()))
    logg.debug('recipient {} balance before: {}'.format(recipient, c.functions.balanceOf(recipient).call()))
    (tx_hash, rcpt) = helper.sign_and_send(
            [
                c.functions.transfer(recipient, value).buildTransaction,
                ],
            )
    logg.debug('sender {} balance after:  {}'.format(signer_address, c.functions.balanceOf(signer_address).call()))
    logg.debug('recipient {} balance after:  {}'.format(recipient, c.functions.balanceOf(recipient).call()))

    if block_last:
        helper.wait_for()

    print(tx_hash)


if __name__ == '__main__':
    main()
