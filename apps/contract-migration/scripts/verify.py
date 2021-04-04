# standard imports
import os
import sys
import logging
import time
import argparse
import sys
import re
import hashlib
import csv
import json
import urllib
import copy

# external imports
import celery
import eth_abi
import confini
from hexathon import (
        strip_0x,
        add_0x,
        )
from chainsyncer.backend import MemBackend
from chainsyncer.driver import HeadSyncer
from chainlib.chain import ChainSpec
from chainlib.eth.connection import EthHTTPConnection
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.eth.block import (
        block_latest,
        block_by_number,
        Block,
        )
from chainlib.eth.hash import keccak256_string_to_hex
from chainlib.eth.address import to_checksum_address
from chainlib.eth.erc20 import ERC20
from chainlib.eth.gas import (
        OverrideGasOracle,
        balance,
        )
from chainlib.eth.tx import TxFactory
from chainlib.eth.rpc import jsonrpc_template
from chainlib.eth.error import EthException
from cic_types.models.person import (
        Person,
        generate_metadata_pointer,
        )
from erc20_single_shot_faucet import SingleShotFaucet

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

config_dir = '/usr/local/etc/cic-syncer'

custodial_tests = [
        'local_key',
        'gas',
        'faucet',
        ]

all_tests = custodial_tests + [
        'accounts_index',
        'balance',
        'metadata',
        ]

argparser = argparse.ArgumentParser(description='daemon that monitors transactions in new blocks')
argparser.add_argument('-p', '--provider', dest='p', type=str, help='chain rpc provider address')
argparser.add_argument('-c', type=str, default=config_dir, help='config root to use')
argparser.add_argument('--old-chain-spec', type=str, dest='old_chain_spec', default='evm:oldchain:1', help='chain spec')
argparser.add_argument('-i', '--chain-spec', type=str, dest='i', help='chain spec')
argparser.add_argument('--meta-provider', type=str, dest='meta_provider', default='http://localhost:63380', help='cic-meta url')
argparser.add_argument('--skip-custodial', dest='skip_custodial', action='store_true', help='skip all custodial verifications')
argparser.add_argument('--exclude', action='append', type=str, default=[], help='skip specified verification')
argparser.add_argument('--include', action='append', type=str, help='include specified verification')
argparser.add_argument('-r', '--registry-address', type=str, dest='r', help='CIC Registry address')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('-x', '--exit-on-error', dest='x', action='store_true', help='Halt exection on error')
argparser.add_argument('-v', help='be verbose', action='store_true')
argparser.add_argument('-vv', help='be more verbose', action='store_true')
argparser.add_argument('user_dir', type=str, help='user export directory')
args = argparser.parse_args(sys.argv[1:])

if args.v == True:
    logging.getLogger().setLevel(logging.INFO)
elif args.vv == True:
    logging.getLogger().setLevel(logging.DEBUG)

config_dir = os.path.join(args.c)
os.makedirs(config_dir, 0o777, True)
config = confini.Config(config_dir, args.env_prefix)
config.process()
# override args
args_override = {
        'CIC_CHAIN_SPEC': getattr(args, 'i'),
        'ETH_PROVIDER': getattr(args, 'p'),
        'CIC_REGISTRY_ADDRESS': getattr(args, 'r'),
        }
config.dict_override(args_override, 'cli flag')
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
logg.debug('config loaded from {}:\n{}'.format(config_dir, config))

celery_app = celery.Celery(backend=config.get('CELERY_RESULT_URL'),  broker=config.get('CELERY_BROKER_URL'))

chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))
chain_str = str(chain_spec)
old_chain_spec = ChainSpec.from_chain_str(args.old_chain_spec)
old_chain_str = str(old_chain_spec)
user_dir = args.user_dir # user_out_dir from import_users.py
meta_url = args.meta_provider
exit_on_error = args.x

active_tests = []
exclude = []
include = args.include
if args.include == None:
    include = all_tests
for t in args.exclude:
    if t not in all_tests:
        raise ValueError('Cannot exclude unknown verification "{}"'.format(t))
    exclude.append(t)
if args.skip_custodial:
    logg.info('will skip all custodial verifications ({})'.format(','.join(custodial_tests)))
    for t in custodial_tests:
        if t not in exclude:
            exclude.append(t)
for t in include:
    if t not in all_tests:
        raise ValueError('Cannot include unknown verification "{}"'.format(t))
    if t not in exclude:
        active_tests.append(t)
        logg.info('will perform verification "{}"'.format(t))

api = None
for t in custodial_tests:
    if t in active_tests:
        from cic_eth.api.api_admin import AdminApi
        api = AdminApi(None)
        logg.info('activating custodial module'.format(t))
        break

cols = os.get_terminal_size().columns


def to_terminalwidth(s):
    ss = s.ljust(int(cols)-1)
    ss += "\r"
    return ss

def default_outfunc(s):
    ss = to_terminalwidth(s)
    sys.stdout.write(ss)
outfunc = default_outfunc
if logg.isEnabledFor(logging.DEBUG):
    outfunc = logg.debug


class VerifierState:

    def __init__(self, item_keys, active_tests=None):
        self.items = {}
        for k in item_keys:
            self.items[k] = 0
        if active_tests == None:
            self.active_tests = copy.copy(item_keys)
        else:
            self.active_tests = copy.copy(active_tests)


    def poke(self, item_key):
        self.items[item_key] += 1


    def __str__(self):
        r = ''
        for k in self.items.keys():
            if k in self.active_tests:
                r += '{}: {}\n'.format(k, self.items[k])
            else:
                r += '{}: skipped\n'.format(k)
        return r


class VerifierError(Exception):

    def __init__(self, e, c):
        super(VerifierError, self).__init__(e)
        self.c = c


    def __str__(self):
        super_error = super(VerifierError, self).__str__()
        return '[{}] {}'.format(self.c, super_error)


class Verifier:

    # TODO: what an awful function signature
    def __init__(self, conn, cic_eth_api, gas_oracle, chain_spec, index_address, token_address, faucet_address, data_dir, exit_on_error=False):
        self.conn = conn
        self.gas_oracle = gas_oracle
        self.chain_spec = chain_spec
        self.index_address = index_address
        self.token_address = token_address
        self.faucet_address = faucet_address
        self.erc20_tx_factory = ERC20(chain_spec, gas_oracle=gas_oracle)
        self.tx_factory = TxFactory(chain_spec, gas_oracle=gas_oracle)
        self.api = cic_eth_api
        self.data_dir = data_dir
        self.exit_on_error = exit_on_error
        self.faucet_tx_factory = SingleShotFaucet(chain_spec, gas_oracle=gas_oracle)

        verifymethods = []
        for k in dir(self):
            if len(k) > 7 and k[:7] == 'verify_':
                logg.debug('verifier has verify method {}'.format(k))
                verifymethods.append(k[7:])

        self.state = VerifierState(verifymethods, active_tests=active_tests)


    def verify_accounts_index(self, address, balance=None):
        tx = self.tx_factory.template(ZERO_ADDRESS, self.index_address)
        data = keccak256_string_to_hex('have(address)')[:8]
        data += eth_abi.encode_single('address', address).hex()
        tx = self.tx_factory.set_code(tx, data)
        tx = self.tx_factory.normalize(tx)
        o = jsonrpc_template()
        o['method'] = 'eth_call'
        o['params'].append(tx)
        r = self.conn.do(o)
        logg.debug('index check for {}: {}'.format(address, r))
        n = eth_abi.decode_single('uint256', bytes.fromhex(strip_0x(r)))
        if n != 1:
            raise VerifierError(n, 'accounts index')


    def verify_balance(self, address, balance):
        o = self.erc20_tx_factory.balance(self.token_address, address)
        r = self.conn.do(o)
        actual_balance = int(strip_0x(r), 16)
        balance = int(balance / 1000000) * 1000000
        logg.debug('balance for {}: {}'.format(address, balance))
        if balance != actual_balance:
            raise VerifierError((actual_balance, balance), 'balance')


    def verify_local_key(self, address, balance=None):
        t = self.api.have_account(address, self.chain_spec)
        r = t.get()
        logg.debug('verify local key result {}'.format(r))
        if r != address:
            raise VerifierError((address, r), 'local key')


    def verify_gas(self, address, balance_token=None):
        o = balance(address)
        r = self.conn.do(o)
        actual_balance = int(strip_0x(r), 16)
        if actual_balance == 0:
            raise VerifierError((address, actual_balance), 'gas')


    def verify_faucet(self, address, balance_token=None):
        o = self.faucet_tx_factory.usable_for(self.faucet_address, address)
        r = self.conn.do(o)
        if self.faucet_tx_factory.parse_usable_for(r):
            raise VerifierError((address, r), 'faucet')


    def verify_metadata(self, address, balance=None):
        k = generate_metadata_pointer(bytes.fromhex(strip_0x(address)), ':cic.person')
        url = os.path.join(meta_url, k)
        logg.debug('verify metadata url {}'.format(url))
        try:
            res = urllib.request.urlopen(url)
        except urllib.error.HTTPError as e:
            raise VerifierError(
                    '({}) {}'.format(url, e),
                    'metadata (person)',
                    )
        b = res.read()
        o_retrieved = json.loads(b.decode('utf-8'))

        upper_address = strip_0x(address).upper()
        f = open(os.path.join(
            self.data_dir,
            'new',
            upper_address[:2],
            upper_address[2:4],
            upper_address + '.json',
            ), 'r'
            )
        o_original = json.load(f)
        f.close()

        if o_original != o_retrieved:
            raise VerifierError(o_retrieved, 'metadata (person)')


    def verify(self, address, balance, debug_stem=None):
  
        for k in active_tests:
            s = '{} {}'.format(debug_stem, k)
            outfunc(s)
            try:
                m = getattr(self, 'verify_{}'.format(k))
                m(address, balance)
            except VerifierError as e:
                logline = 'verification {} failed for {}: {}'.format(k, address, str(e))
                if self.exit_on_error:
                    logg.critical(logline)
                    sys.exit(1)
                logg.error(logline)
                self.state.poke(k)


    def __str__(self):
        return str(self.state)


def main():
    global chain_str, block_offset, user_dir
    
    conn = EthHTTPConnection(config.get('ETH_PROVIDER'))
    gas_oracle = OverrideGasOracle(conn=conn, limit=8000000)

    # Get Token registry address
    txf = TxFactory(chain_spec, signer=None, gas_oracle=gas_oracle, nonce_oracle=None)
    tx = txf.template(ZERO_ADDRESS, config.get('CIC_REGISTRY_ADDRESS'))

    # TODO: replace with cic-eth-registry
    registry_addressof_method = keccak256_string_to_hex('addressOf(bytes32)')[:8]
    data = add_0x(registry_addressof_method)
    data += eth_abi.encode_single('bytes32', b'TokenRegistry').hex()
    txf.set_code(tx, data)
    
    o = jsonrpc_template()
    o['method'] = 'eth_call'
    o['params'].append(txf.normalize(tx))
    o['params'].append('latest')
    r = conn.do(o)
    token_index_address = to_checksum_address(eth_abi.decode_single('address', bytes.fromhex(strip_0x(r))))
    logg.info('found token index address {}'.format(token_index_address))

    data = add_0x(registry_addressof_method)
    data += eth_abi.encode_single('bytes32', b'AccountRegistry').hex()
    txf.set_code(tx, data)
    
    o = jsonrpc_template()
    o['method'] = 'eth_call'
    o['params'].append(txf.normalize(tx))
    o['params'].append('latest')
    r = conn.do(o)
    account_index_address = to_checksum_address(eth_abi.decode_single('address', bytes.fromhex(strip_0x(r))))
    logg.info('found account index address {}'.format(account_index_address))

    data = add_0x(registry_addressof_method)
    data += eth_abi.encode_single('bytes32', b'Faucet').hex()
    txf.set_code(tx, data)
    
    o = jsonrpc_template()
    o['method'] = 'eth_call'
    o['params'].append(txf.normalize(tx))
    o['params'].append('latest')
    r = conn.do(o)
    faucet_address = to_checksum_address(eth_abi.decode_single('address', bytes.fromhex(strip_0x(r))))
    logg.info('found faucet {}'.format(faucet_address))



    # Get Sarafu token address
    tx = txf.template(ZERO_ADDRESS, token_index_address)
    data = add_0x(registry_addressof_method)
    h = hashlib.new('sha256')
    h.update(b'SRF')
    z = h.digest()
    data += eth_abi.encode_single('bytes32', z).hex()
    txf.set_code(tx, data)
    o = jsonrpc_template()
    o['method'] = 'eth_call'
    o['params'].append(txf.normalize(tx))
    o['params'].append('latest')
    r = conn.do(o)
    sarafu_token_address = to_checksum_address(eth_abi.decode_single('address', bytes.fromhex(strip_0x(r))))
    logg.info('found token address {}'.format(sarafu_token_address))

    balances = {}
    f = open('{}/balances.csv'.format(user_dir, 'r'))
    i = 0
    while True:
        l = f.readline()
        if l == None:
            break
        r = l.split(',')
        try:
            address = to_checksum_address(r[0])
            #sys.stdout.write('loading balance {} {}'.format(i, address).ljust(200) + "\r")
            outfunc('loading balance {} {}'.format(i, address)) #.ljust(200))
        except ValueError:
            break
        balance = int(r[1].rstrip())
        balances[address] = balance
        i += 1

    f.close()

    verifier = Verifier(conn, api, gas_oracle, chain_spec, account_index_address, sarafu_token_address, faucet_address, user_dir, exit_on_error)

    user_new_dir = os.path.join(user_dir, 'new')
    i = 0
    for x in os.walk(user_new_dir):
        for y in x[2]:
            if y[len(y)-5:] != '.json':
                continue
            filepath = os.path.join(x[0], y)
            f = open(filepath, 'r')
            try:
                o = json.load(f)
            except json.decoder.JSONDecodeError as e:
                f.close()
                logg.error('load error for {}: {}'.format(y, e))
                continue
            f.close()

            u = Person.deserialize(o)
            #logg.debug('data {}'.format(u.identities['evm']))

            subchain_str = '{}:{}'.format(chain_spec.common_name(), chain_spec.network_id())
            new_address = u.identities['evm'][subchain_str][0]
            subchain_str = '{}:{}'.format(old_chain_spec.common_name(), old_chain_spec.network_id())
            old_address = u.identities['evm'][subchain_str][0]
            balance = 0
            try:
                balance = balances[old_address]
            except KeyError:
                logg.info('no old balance found for {}, assuming 0'.format(old_address))

            s = 'checking {}: {} -> {} = {}'.format(i, old_address, new_address, balance)

            verifier.verify(new_address, balance, debug_stem=s)
            i += 1

    print(verifier)


if __name__ == '__main__':
    main()
