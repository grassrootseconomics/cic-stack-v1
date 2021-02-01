# standard imports
import os
import sys
import logging
import time
import argparse
import sys
import re

# third-party imports
import confini
import celery
import rlp
import web3
from web3 import HTTPProvider, WebsocketProvider
from cic_registry import CICRegistry
from cic_registry.chain import ChainSpec
from cic_registry import zero_address
from cic_registry.chain import ChainRegistry
from cic_registry.error import UnknownContractError
from cic_bancor.bancor import BancorRegistryClient

# local imports
import cic_eth
from cic_eth.eth import RpcClient
from cic_eth.db import SessionBase
from cic_eth.db import Otx
from cic_eth.db import TxConvertTransfer
from cic_eth.db.models.tx import TxCache
from cic_eth.db.enum import StatusEnum
from cic_eth.db import dsn_from_config
from cic_eth.queue.tx import get_paused_txs
from cic_eth.sync import Syncer
from cic_eth.sync.error import LoopDone
from cic_eth.db.error import UnknownConvertError
from cic_eth.eth.util import unpack_signed_raw_tx
from cic_eth.eth.task import create_check_gas_and_send_task
from cic_eth.sync.backend import SyncerBackend
from cic_eth.eth.token import unpack_transfer
from cic_eth.eth.token import unpack_transferfrom
from cic_eth.eth.account import unpack_gift

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()
logging.getLogger('websockets.protocol').setLevel(logging.CRITICAL)
logging.getLogger('web3.RequestManager').setLevel(logging.CRITICAL)
logging.getLogger('web3.providers.WebsocketProvider').setLevel(logging.CRITICAL)
logging.getLogger('web3.providers.HTTPProvider').setLevel(logging.CRITICAL)


config_dir = os.path.join('/usr/local/etc/cic-eth')

argparser = argparse.ArgumentParser(description='daemon that monitors transactions in new blocks')
argparser.add_argument('-c', type=str, default=config_dir, help='config root to use')
argparser.add_argument('-i', '--chain-spec', type=str, dest='i', help='chain spec')
argparser.add_argument('--abi-dir', dest='abi_dir', type=str, help='Directory containing bytecode and abi')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('-q', type=str, default='cic-eth', help='celery queue to submit transaction tasks to')
argparser.add_argument('-v', help='be verbose', action='store_true')
argparser.add_argument('-vv', help='be more verbose', action='store_true')
argparser.add_argument('mode', type=str, help='sync mode: (head|history)', default='head')
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
        'ETH_ABI_DIR': getattr(args, 'abi_dir'),
        'CIC_CHAIN_SPEC': getattr(args, 'i'),
        }
config.dict_override(args_override, 'cli flag')
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
logg.debug('config loaded from {}:\n{}'.format(config_dir, config))

app = celery.Celery(backend=config.get('CELERY_RESULT_URL'),  broker=config.get('CELERY_BROKER_URL'))

queue = args.q

dsn = dsn_from_config(config)
SessionBase.connect(dsn)

# TODO: There is too much code in this file, split it up

transfer_callbacks = []
for cb in config.get('TASKS_TRANSFER_CALLBACKS', '').split(','):
    task_split = cb.split(':')
    task_queue = queue
    if len(task_split) > 1:
        task_queue = task_split[0]
    task_pair = (task_split[1], task_queue)
    transfer_callbacks.append(task_pair)


# TODO: move to contract registry
__convert_log_hash = '0x7154b38b5dd31bb3122436a96d4e09aba5b323ae1fd580025fab55074334c095' # keccak256(Conversion(address,address,address,uint256,uint256,address)
__account_registry_add_log_hash = '0x5ed3bdd47b9af629827a8d129aa39c870b10c03f0153fe9ddb8e84b665061acd' # keccak256(AccountAdded(address,uint256))

__transfer_method_signature = '0xa9059cbb' # keccak256(transfer(address,uint256))
__transferfrom_method_signature = '0x23b872dd' # keccak256(transferFrom(address,address,uint256))
__giveto_method_signature = '0x63e4bff4' # keccak256(giveTo(address))

# TODO: move to bancor package
def parse_convert_log(w3, entry):
    data = entry.data[2:]
    from_amount = int(data[:64], 16)
    to_amount = int(data[64:128], 16)
    holder_address_hex_raw = '0x' + data[-40:]
    holder_address_hex = w3.toChecksumAddress(holder_address_hex_raw)
    o = {
            'from_amount': from_amount,
            'to_amount': to_amount,
            'holder_address': holder_address_hex
            }
    logg.debug('parsed convert log {}'.format(o))
    return o


def registration_filter(w3, tx, rcpt, chain_spec):
    registered_address = None
    for l in rcpt['logs']:
        event_topic_hex = l['topics'][0].hex()
        if event_topic_hex == __account_registry_add_log_hash:
            address_bytes = l.topics[1][32-20:]
            address = web3.Web3.toChecksumAddress(address_bytes.hex())
            logg.debug('request token gift to {}'.format(address))
            s = celery.signature(
                'cic_eth.eth.account.gift',
                [
                    address,
                    str(chain_spec),
                    ],
                queue=queue,
                )
            s.apply_async()


def convert_filter(w3, tx, rcpt, chain_spec):
    destination_token_address = None
    recipient_address = None
    amount = 0
    for l in rcpt['logs']:
        event_topic_hex = l['topics'][0].hex()
        if event_topic_hex == __convert_log_hash:
            tx_hash_hex = tx['hash'].hex()
            try:
                convert_transfer = TxConvertTransfer.get(tx_hash_hex)
            except UnknownConvertError:
                logg.warning('skipping unknown convert tx {}'.format(tx_hash_hex))
                continue
            if convert_transfer.transfer_tx_hash != None:
                logg.warning('convert tx {} cache record already has transfer hash {}, skipping'.format(tx_hash_hex, convert_transfer.transfer_hash))
                continue
            recipient_address = convert_transfer.recipient_address
            logg.debug('found convert event {} recipient'.format(tx_hash_hex, recipient_address))
            r = parse_convert_log(l)
            destination_token_address = l['topics'][3][-20:]

    if destination_token_address == zero_address or destination_token_address == None:
        return None

    destination_token_address_hex = destination_token_address.hex()
    s = celery.signature(
            'cic_eth.eth.bancor.transfer_converted',
            [
                [{
                    'address': w3.toChecksumAddress(destination_token_address_hex),
                    }],
                r['holder_address'],
                recipient_address,
                r['to_amount'],
                tx_hash_hex,
                str(chain_spec),
                ],
                queue=queue,
            )
    logg.info('sending tx signature {}'.format(s))
    t = s.apply_async()
    logg.debug('submitted transfer after convert task uuid {} {}'.format(t, t.successful()))
    return t


def tx_filter(w3, tx, rcpt, chain_spec):
    tx_hash_hex = tx.hash.hex()
    otx = Otx.load(tx_hash_hex)
    if otx == None:
        logg.debug('tx {} not found locally, skipping'.format(tx_hash_hex))
        return None
    logg.info('otx found {}'.format(otx.tx_hash))
    s = celery.signature(
            'cic_eth.queue.tx.set_final_status',
            [
                tx_hash_hex,
                rcpt.blockNumber,
                rcpt.status == 0,
                ],
            queue=queue,
            )
    t = s.apply_async()
    return t


# TODO: replace with registry call instead
def get_token_symbol(w3, address):
    #token = CICRegistry.get_address(CICRegistry.chain_spec, tx['to'])
    logg.warning('token verification missing')
    c = w3.eth.contract(abi=CICRegistry.abi('ERC20'), address=address)
    return c.functions.symbol().call()


# TODO: replace with registry call instead
def get_token_decimals(w3, address):
    #token = CICRegistry.get_address(CICRegistry.chain_spec, tx['to'])
    logg.warning('token verification missing')
    c = w3.eth.contract(abi=CICRegistry.abi('ERC20'), address=address)
    return c.functions.decimals().call()


def callbacks_filter(w3, tx, rcpt, chain_spec):
    transfer_data = None
    if len(tx.input) < 10:
        logg.debug('callbacks filter data length not sufficient for method signature in tx {}, skipping'.format(tx['hash']))
        return

    logg.debug('checking callbacks filter input {}'.format(tx.input[:10]))

    transfer_type = 'transfer'
    method_signature = tx.input[:10]
    if method_signature == __transfer_method_signature:
        transfer_data = unpack_transfer(tx.input)
        transfer_data['from'] = tx['from']
        transfer_data['token_address'] = tx['to']
    elif method_signature == __transferfrom_method_signature:
        transfer_type = 'transferfrom'
        transfer_data = unpack_transferfrom(tx.input)
        transfer_data['token_address'] = tx['to']
    elif method_signature == __giveto_method_signature:
        transfer_type = 'tokengift'
        transfer_data = unpack_gift(tx.input)
        for l in rcpt.logs:
            if l.topics[0].hex() == '0x45c201a59ac545000ead84f30b2db67da23353aa1d58ac522c48505412143ffa':
                transfer_data['amount'] = web3.Web3.toInt(hexstr=l.data)
                token_address_bytes = l.topics[2][32-20:]
                transfer_data['token_address'] = web3.Web3.toChecksumAddress(token_address_bytes.hex())
                transfer_data['from'] = rcpt.to

    if transfer_data != None:
        for tc in transfer_callbacks:
            token_symbol = None
            try:
                logg.debug('checking token {}'.format(transfer_data['token_address']))
                token_symbol = get_token_symbol(w3, transfer_data['token_address'])
                token_decimals = get_token_decimals(w3, transfer_data['token_address'])
                logg.debug('calling transfer callback {}:{} for tx {}'.format(tc[1], tc[0], tx['hash']))
            except UnknownContractError:
                logg.debug('callback filter {}:{} skipping "transfer" method on unknown contract {} tx {}'.format(tc[1], tc[0], transfer_data['to'], tx.hash.hex()))
                continue
            result = {
                'hash': tx.hash.hex(),
                'sender': transfer_data['from'],
                'recipient': transfer_data['to'],
                'source_value': transfer_data['amount'],
                'destination_value': transfer_data['amount'],
                'source_token': transfer_data['token_address'],
                'destination_token': transfer_data['token_address'],
                'source_token_symbol': token_symbol,
                'destination_token_symbol': token_symbol,
                'source_token_decimals': token_decimals,
                'destination_token_decimals': token_decimals,
                'chain': str(chain_spec),
                    }
            s = celery.signature(
                tc[0],
                [
                    result,
                    transfer_type,
                    int(rcpt.status == 0),
                ],
                queue=tc[1],
                )
            s.apply_async()


class GasFilter:

    def __init__(self, gas_provider):
        self.gas_provider = gas_provider

    def filter(self, w3, tx, rcpt, chain_str):
        tx_hash_hex = tx.hash.hex()
        if tx['value'] > 0:
            logg.debug('gas refill tx {}'.format(tx_hash_hex))
            session = SessionBase.create_session()
            q = session.query(TxCache.recipient)
            q = q.join(Otx)
            q = q.filter(Otx.tx_hash==tx_hash_hex)
            r = q.first()

            session.close()

            if r == None:
                logg.warning('unsolicited gas refill tx {}'.format(tx_hash_hex))
                return

            chain_spec = ChainSpec.from_chain_str(chain_str)
            txs = get_paused_txs(StatusEnum.WAITFORGAS, r[0], chain_spec.chain_id())

            if len(txs) > 0:
                logg.info('resuming gas-in-waiting txs for {}: {}'.format(r[0], txs.keys()))
                s = create_check_gas_and_send_task(
                        list(txs.values()),
                        str(chain_str),
                        r[0],
                        0,
                        tx_hashes_hex=list(txs.keys()),
                        queue=queue,
                )
                s.apply_async()


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


def main(): 

    chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))
    c = RpcClient(chain_spec)

    CICRegistry.init(c.w3, config.get('CIC_REGISTRY_ADDRESS'), chain_spec)
    CICRegistry.add_path(config.get('ETH_ABI_DIR'))
    chain_registry = ChainRegistry(chain_spec)
    CICRegistry.add_chain_registry(chain_registry)

    if config.get('ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER') != None:
        CICRegistry.add_role(chain_spec, config.get('ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER'), 'AccountRegistry', True)

    syncers = []
    block_offset = c.w3.eth.blockNumber
    chain = str(chain_spec)

    if SyncerBackend.first(chain):
        from cic_eth.sync.history import HistorySyncer
        backend = SyncerBackend.initial(chain, block_offset)
        syncer = HistorySyncer(backend) 
        syncers.append(syncer)

    if args.mode == 'head':
        from cic_eth.sync.head import HeadSyncer
        block_sync = SyncerBackend.live(chain, block_offset+1)
        syncers.append(HeadSyncer(block_sync))
    elif args.mode == 'history':
        from cic_eth.sync.history import HistorySyncer
        backends = SyncerBackend.resume(chain, block_offset+1)
        for backend in backends:
            syncers.append(HistorySyncer(backend))
        if len(syncers) == 0:
            logg.info('found no unsynced history. terminating')
            sys.exit(0)
    else:
        sys.stderr.write("unknown mode '{}'\n".format(args.mode))
        sys.exit(1)

#    bancor_registry_contract = CICRegistry.get_contract(chain_spec, 'BancorRegistry', interface='Registry')
#    bancor_chain_registry = CICRegistry.get_chain_registry(chain_spec)
#    bancor_registry = BancorRegistryClient(c.w3, bancor_chain_registry, config.get('ETH_ABI_DIR'))
#    bancor_registry.load() 
 
    i = 0
    for syncer in syncers:
        logg.debug('running syncer index {}'.format(i))
        gas_filter = GasFilter(c.gas_provider()).filter
        syncer.filter.append(gas_filter)
        syncer.filter.append(registration_filter)
        syncer.filter.append(callbacks_filter)
        # TODO: the two following filter functions break the filter loop if return uuid. Pro: less code executed. Con: Possibly unintuitive flow break
        syncer.filter.append(tx_filter)
        syncer.filter.append(convert_filter)

        try:
            syncer.loop(int(config.get('SYNCER_LOOP_INTERVAL')))
        except LoopDone as e:
            sys.stderr.write("sync '{}' done at block {}\n".format(args.mode, e))

        i += 1

    sys.exit(0)


if __name__ == '__main__':
    main()
