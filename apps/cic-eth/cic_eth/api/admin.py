# standard imports
import logging
import sys

# external imports
import celery
from chainlib.eth.constant import (
        ZERO_ADDRESS,
        )
from cic_eth_registry import CICRegistry
from cic_eth_registry.erc20 import ERC20Token
from cic_eth_registry.error import UnknownContractError
from chainlib.eth.address import to_checksum_address
from chainlib.eth.contract import code
from chainlib.eth.tx import (
        transaction,
        receipt,
        unpack,
        )
from chainlib.hash import keccak256_hex_to_hex
from hexathon import (
        strip_0x,
        add_0x,
        uniform as hex_uniform,
        )
from chainlib.eth.gas import balance
from chainqueue.db.enum import (
        StatusEnum,
        StatusBits,
        is_alive,
        is_error_status,
        status_str,
    )
from chainqueue.error import TxStateChangeError
from eth_erc20 import ERC20

# local imports
from cic_eth.db.models.base import SessionBase
from cic_eth.db.models.role import AccountRole
from cic_eth.db.models.nonce import Nonce
from cic_eth.error import InitializationError
from cic_eth.queue.query import get_tx_local

app = celery.current_app

#logg = logging.getLogger(__file__)
logg = logging.getLogger()

local_fail = StatusBits.LOCAL_ERROR | StatusBits.NODE_ERROR | StatusBits.UNKNOWN_ERROR


class AdminApi:
    """Provides an interface to view and manipulate existing transaction tasks and system runtime settings.

    :param rpc_client: Rpc client to use for blockchain connections.
    :type rpc_client: cic_eth.eth.rpc.RpcClient
    :param queue: Name of worker queue to submit tasks to
    :type queue: str
    """
    def __init__(self, rpc, queue='cic-eth', call_address=ZERO_ADDRESS):
        self.rpc = rpc
        self.queue = queue
        self.call_address = call_address


    def proxy_do(self, chain_spec, o):
        s_proxy = celery.signature(
                'cic_eth.task.rpc_proxy',
                [
                    chain_spec.asdict(),
                    o,
                    'default',
                    ],
                queue=self.queue
                )
        return s_proxy.apply_async()

    
    def registry(self):
        s_registry = celery.signature(
                'cic_eth.task.registry',
                [],
                queue=self.queue
                )
        return s_registry.apply_async()


    def unlock(self, chain_spec, address, flags=None):
        s_unlock = celery.signature(
            'cic_eth.admin.ctrl.unlock',
            [
                None,
                chain_spec.asdict(),
                address,
                flags,
                ],
            queue=self.queue,
            )
        return s_unlock.apply_async()


    def lock(self, chain_spec, address, flags=None):
        s_lock = celery.signature(
            'cic_eth.admin.ctrl.lock',
            [
                None,
                chain_spec.asdict(),
                address,
                flags,
                ],
            queue=self.queue,
            )
        return s_lock.apply_async()


    def get_lock(self):
        s_lock = celery.signature(
            'cic_eth.queue.lock.get_lock',
            [],
            queue=self.queue,
            )
        return s_lock.apply_async()


    def tag_account(self, chain_spec, tag, address):
        """Persistently associate an address with a plaintext tag.

        Some tags are known by the system and is used to resolve addresses to use for certain transactions. 

        :param tag: Address tag
        :type tag: str
        :param address_hex: Ethereum address to tag
        :type address_hex: str, 0x-hex
        :raises ValueError: Invalid checksum address
        """
        s_tag = celery.signature(
            'cic_eth.eth.account.set_role',
            [
                tag,
                address,
                chain_spec.asdict(),
                ],
            queue=self.queue,
            )
        return s_tag.apply_async()


    def get_tag_account(self, chain_spec, tag=None, address=None):
        if address != None:
            s_tag = celery.signature(
                'cic_eth.eth.account.role',
                [
                    address,
                    chain_spec.asdict(),
                    ],
                queue=self.queue,
                )

        else:
            s_tag = celery.signature(
                'cic_eth.eth.account.role_account',
                [
                    tag,
                    chain_spec.asdict(),
                ],
                queue=self.queue,
                )

        return s_tag.apply_async()


    def have_account(self, address_hex, chain_spec):
        s_have = celery.signature(
            'cic_eth.eth.account.have',
            [
                address_hex,
                chain_spec.asdict(),
                ],
            queue=self.queue,
            )
        return s_have.apply_async()


    def resend(self, tx_hash_hex, chain_spec, in_place=True, unlock=False, gas_price=None, gas_ratio=1.01, force=False):

        if gas_price != None:
            logg.debug('resend {} gas price {}'.format(tx_hash_hex, gas_price))
        else:
            logg.debug('resend {} gas ratio {}'.format(tx_hash_hex, gas_ratio))

        s_get_tx_cache = celery.signature(
            'cic_eth.queue.query.get_tx_cache',
            [
                chain_spec.asdict(),
                tx_hash_hex,
                ],
            queue=self.queue,
            )

        # TODO: This check should most likely be in resend task itself
        tx_dict = s_get_tx_cache.apply_async().get()
        #if not is_alive(getattr(StatusEnum, tx_dict['status_code'])):
        if not force and not is_alive(tx_dict['status_code']):
            raise TxStateChangeError('Cannot resend mined or obsoleted transaction'.format(tx_hash_hex))
        
        if not in_place:
            raise NotImplementedError('resend as new not yet implemented')

        s = celery.signature(
            'cic_eth.eth.gas.resend_with_higher_gas',
            [
                chain_spec.asdict(),
                gas_price,
                gas_ratio,
                ],
            queue=self.queue,
            )

        s_manual = celery.signature(
            'cic_eth.queue.state.set_manual',
            [
                chain_spec.asdict(),
                tx_hash_hex,
                ],
            queue=self.queue,
            )
        s_manual.link(s)

        if unlock:
            s_gas = celery.signature(
                'cic_eth.admin.ctrl.unlock_send',
                [
                    chain_spec.asdict(),
                    tx_dict['sender'],
                ],
                queue=self.queue,
                )
            s.link(s_gas)

        return s_manual.apply_async()
                    

    def check_nonce(self, chain_spec, address):
        s = celery.signature(
                'cic_eth.queue.query.get_account_tx',
                [
                    chain_spec.asdict(),
                    address,
                    ],
                kwargs = {
                    'as_sender': True,
                    'as_recipient': False,
                },
                queue=self.queue,
                )
        txs = s.apply_async().get()

        blocking_tx = None
        blocking_nonce = None
        nonce_otx = 0
        last_nonce = -1
        for k in txs.keys():
            s_get_tx = celery.signature(
                    'cic_eth.queue.query.get_tx',
                    [
                        chain_spec.asdict(),
                        k,
                        ],
                    queue=self.queue,
                    )
            tx = s_get_tx.apply_async().get()
            logg.debug('checking nonce {} (previous {})'.format(tx['nonce'], last_nonce))
            nonce_otx = tx['nonce']
            if not is_alive(tx['status']) and tx['status'] & local_fail > 0:
                logg.info('permanently errored {} nonce {} status {}'.format(k, nonce_otx, status_str(tx['status'])))
                blocking_tx = k
                blocking_nonce = nonce_otx
            elif nonce_otx - last_nonce > 1:
                logg.debug('tx {}'.format(tx))
                tx_obj = unpack(bytes.fromhex(strip_0x(tx['signed_tx'])), chain_spec)
                logg.error('nonce gap; {} followed {} for account {}'.format(nonce_otx, last_nonce, tx_obj['from']))
                blocking_tx = k
                blocking_nonce = nonce_otx
                break
            last_nonce = nonce_otx

        return {
            'nonce': {
                #'network': nonce_cache,
                'queue': nonce_otx,
                #'cache': nonce_cache,
                'blocking': blocking_nonce,
            },
            'tx': {
                'blocking': add_0x(blocking_tx),
            }
        }


    # TODO: is risky since it does not validate that there is actually a nonce problem?
    def fix_nonce(self, chain_spec, address, nonce):
        s = celery.signature(
                'cic_eth.queue.query.get_account_tx',
                [
                    chain_spec.asdict(),
                    address,
                    ],
                kwargs={
                    'as_sender': True,
                    'as_recipient': False,
                    },
                queue=self.queue,
                )
        txs = s.apply_async().get()

        tx_hash_hex = None
        session = SessionBase.create_session()
        for k in txs.keys():
            tx_dict = get_tx_local(chain_spec, k, session=session)
            if tx_dict['nonce'] == nonce:
                tx_hash_hex = k
        session.close()

        s_nonce = celery.signature(
                'cic_eth.admin.nonce.shift_nonce',
                [
                    chain_spec.asdict(),
                    tx_hash_hex, 
                ],
                queue=self.queue
                )
        return s_nonce.apply_async()


    def account(self, chain_spec, address, include_sender=True, include_recipient=True, renderer=None, status=None, not_status=None, offset=None, limit=None, w=sys.stdout):
        """Lists locally originated transactions for the given Ethereum address.

        Performs a synchronous call to the Celery task responsible for performing the query.

        :param address: Ethereum address to return transactions for
        :type address: str, 0x-hex
        """

        address = add_0x(hex_uniform(strip_0x(address)))
        last_nonce = -1
        s = celery.signature(
                'cic_eth.queue.query.get_account_tx',
                [
                    chain_spec.asdict(),
                    address,
                    ],
                kwargs={
                    'status': status,
                    'not_status': not_status,
                    'offset': offset,
                    'limit': limit,
                },
                queue=self.queue,
                )
        txs = s.apply_async().get()

        tx_dict_list = []
        for tx_hash in txs.keys():
            errors = []
            s = celery.signature(
                    'cic_eth.queue.query.get_tx_cache',
                    [
                        chain_spec.asdict(),
                        tx_hash,
                        ],
                    queue=self.queue,
                    )
            tx_dict = s.apply_async().get()
            if tx_dict['sender'] == address:
                if tx_dict['nonce'] - last_nonce > 1:
                    logg.error('nonce gap; {} followed {} for address {} tx {}'.format(tx_dict['nonce'], last_nonce, tx_dict['sender'], tx_hash))
                    errors.append('nonce')
                elif tx_dict['nonce'] == last_nonce:
                    logg.info('nonce {} duplicate for address {} in tx {}'.format(tx_dict['nonce'], tx_dict['sender'], tx_hash))
                last_nonce = tx_dict['nonce']
                if not include_sender:
                    logg.debug('skipping sender tx {}'.format(tx_dict['tx_hash']))
                    continue
            elif tx_dict['recipient'] == address and not include_recipient:
                logg.debug('skipping recipient tx {}'.format(tx_dict['tx_hash']))
                continue

            o = {
                'nonce': tx_dict['nonce'], 
                'tx_hash': tx_dict['tx_hash'],
                'status': tx_dict['status'],
                'date_updated': tx_dict['date_updated'],
                'errors': errors,
                    }
            if renderer != None:
                r = renderer(o)
                w.write(r + '\n')
            else:
                tx_dict_list.append(o)

        return tx_dict_list

    def txs_latest(self, chain_spec, count=10, renderer=None, status=None, not_status=None, offset=None, limit=None, w=sys.stdout):
        """Lists latest locally originated transactions.

        Performs a synchronous call to the Celery task responsible for performing the query.
        """

        last_nonce = -1
        s = celery.signature(
                'cic_eth.queue.query.get_latest_txs',
                [
                    chain_spec.asdict(),
                ],
                kwargs={
                    "count": count,
                    "status": status,
                    "not_status": not_status,
                    "offset": offset,
                    "limit": limit,
                },
                queue=self.queue,
                )
        txs = s.apply_async().get()
        tx_dict_list = []
        for tx_hash in txs.keys():
            errors = []
            s = celery.signature(
                    'cic_eth.queue.query.get_tx_cache',
                    [
                        chain_spec.asdict(),
                        tx_hash,
                        ],
                    queue=self.queue,
                    )
            tx_dict = s.apply_async().get()
            if tx_dict['nonce'] - last_nonce > 1:
                logg.error(f"nonce gap; {tx_dict['nonce']} followed {last_nonce} for address {tx_dict['sender']} tx {tx_hash}")
                errors.append('nonce')
            elif tx_dict['nonce'] == last_nonce:
                logg.info(f"nonce {tx_dict['nonce']} duplicate for address {tx_dict['sender']} in tx {tx_hash}")
            last_nonce = tx_dict['nonce']

            
            o = {
                'nonce': tx_dict['nonce'], 
                'tx_hash': tx_dict['tx_hash'],
                'status': tx_dict['status'],
                'date_updated': tx_dict['date_updated'],
                'date_created': tx_dict['date_created'],
                'errors': errors,
                    }
            if renderer != None:
                r = renderer(o)
                w.write(r + '\n')
            else:
                tx_dict_list.append(o)

        return tx_dict_list

    # TODO: Add exception upon non-existent tx aswell as invalid tx data to docstring 
    # TODO: This method is WAY too long
    def tx(self, chain_spec, tx_hash=None, tx_raw=None, registry=None, renderer=None, w=sys.stdout):
        """Output local and network details about a given transaction with local origin.

        If the transaction hash is given, the raw trasnaction data will be retrieved from the local transaction queue backend. Otherwise the raw transaction data must be provided directly. Only one of transaction hash and transaction data can be passed.

        :param chain_spec: Chain spec of the transaction's chain context 
        :type chain_spec: cic_registry.chain.ChainSpec
        :param tx_hash: Transaction hash of transaction to parse and view
        :type tx_hash: str, 0x-hex
        :param tx_raw: Signed raw transaction data to parse and view
        :type tx_raw: str, 0x-hex
        :raises ValueError: Both tx_hash and tx_raw are passed
        :return: Transaction details
        :rtype: dict
        """
        problems = []

        if tx_hash != None and tx_raw != None:
            ValueError('Specify only one of hash or raw tx')

        if tx_raw != None:
            tx_hash = add_0x(keccak256_hex_to_hex(tx_raw))

        s = celery.signature(
            'cic_eth.queue.query.get_tx_cache',
            [
                chain_spec.asdict(),
                tx_hash,
                ],
            queue=self.queue,
            )
    
        t = s.apply_async()
        tx = t.get()

        source_token = None
        if tx['source_token'] != ZERO_ADDRESS:
            source_token_declaration = None
            if registry != None:
                try:
                    source_token_declaration = registry.by_address(tx['source_token'], sender_address=self.call_address)
                except UnknownContractError:
                    logg.warning('unknown source token contract {} (direct)'.format(tx['source_token']))
            else:
                s = celery.signature(
                        'cic_eth.task.registry_address_lookup',
                        [
                            chain_spec.asdict(),
                            tx['source_token'],
                            ],
                        queue=self.queue
                        )
                t = s.apply_async()
                source_token_declaration = t.get()

            if source_token_declaration != None:
                logg.warning('found declarator record for source token {} but not checking validity'.format(tx['source_token']))
                source_token = ERC20Token(chain_spec, self.rpc, tx['source_token'])
                logg.debug('source token set tup {}'.format(source_token))



        destination_token = None
        if tx['destination_token'] != ZERO_ADDRESS:
            destination_token_declaration = None
            if registry != None:
                try:
                    destination_token_declaration = registry.by_address(tx['destination_token'], sender_address=self.call_address)
                except UnknownContractError:
                    logg.warning('unknown destination token contract {}'.format(tx['destination_token']))
            else:
                s = celery.signature(
                        'cic_eth.task.registry_address_lookup',
                        [
                            chain_spec.asdict(),
                            tx['destination_token'],
                            ],
                        queue=self.queue
                        )
                t = s.apply_async()
                destination_token_declaration = t.get()
            if destination_token_declaration != None:
                logg.warning('found declarator record for destination token {} but not checking validity'.format(tx['destination_token']))
                destination_token = ERC20Token(chain_spec, self.rpc, tx['destination_token'])

        tx['sender_description'] = 'Custodial account'
        tx['recipient_description'] = 'Custodial account'

        o = code(tx['sender'])
        t = self.proxy_do(chain_spec, o)
        r = t.get()
        if len(strip_0x(r, allow_empty=True)) > 0:
            if registry != None:
                try:
                    sender_contract = registry.by_address(tx['sender'], sender_address=self.call_address)
                    tx['sender_description'] = 'Contract at {}'.format(tx['sender'])
                except UnknownContractError:
                    tx['sender_description'] = 'Unknown contract'
                except KeyError as e:
                    tx['sender_description'] = 'Unknown contract'
            else:
                s = celery.signature(
                        'cic_eth.task.registry_address_lookup',
                        [
                            chain_spec.asdict(),
                            tx['sender'],
                            ],
                        queue=self.queue
                        )
                t = s.apply_async()
                tx['sender_description'] = t.get()
                if tx['sender_description'] == None:
                    tx['sender_description'] = 'Unknown contract'


        else:
            s = celery.signature(
                    'cic_eth.eth.account.have',
                    [
                        tx['sender'],
                        chain_spec.asdict(),
                        ],
                    queue=self.queue,
                    )
            t = s.apply_async()
            account = t.get()
            if account == None:
                tx['sender_description'] = 'Unknown account'
            else:
                s = celery.signature(
                    'cic_eth.eth.account.role',
                    [
                        tx['sender'],
                        chain_spec.asdict(),
                        ],
                    queue=self.queue,
                    )
                t = s.apply_async()
                role = t.get()[0][1]
                if role != None:
                    tx['sender_description'] = role

        o = code(tx['recipient'])
        t = self.proxy_do(chain_spec, o)
        r = t.get()
        if len(strip_0x(r, allow_empty=True)) > 0:
            if registry != None:
                try:
                    recipient_contract = registry.by_address(tx['recipient'])
                    tx['recipient_description'] = 'Contract at {}'.format(tx['recipient'])
                except UnknownContractError as e:
                    tx['recipient_description'] = 'Unknown contract'
                except KeyError as e:
                    tx['recipient_description'] = 'Unknown contract'
            else:
                s = celery.signature(
                        'cic_eth.task.registry_address_lookup',
                        [
                            chain_spec.asdict(),
                            tx['recipient'],
                            ],
                        queue=self.queue
                        )
                t = s.apply_async()
                tx['recipient_description'] = t.get()
                if tx['recipient_description'] == None:
                    tx['recipient_description'] = 'Unknown contract'

        else:
            s = celery.signature(
                    'cic_eth.eth.account.have',
                    [
                        tx['recipient'],
                        chain_spec.asdict(),
                        ],
                    queue=self.queue,
                    )
            t = s.apply_async()
            account = t.get()
            if account == None:
                tx['recipient_description'] = 'Unknown account'
            else:
                s = celery.signature(
                    'cic_eth.eth.account.role',
                    [
                        tx['recipient'],
                        chain_spec.asdict(),
                        ],
                    queue=self.queue,
                    )
                t = s.apply_async()
                role = t.get()[0][1]
                if role != None:
                    tx['recipient_description'] = role

        erc20_c = ERC20(chain_spec)
        if source_token != None:
            tx['source_token_symbol'] = source_token.symbol
            o = erc20_c.balance_of(tx['source_token'], tx['sender'], sender_address=self.call_address)
            r = self.rpc.do(o)
            tx['sender_token_balance'] = erc20_c.parse_balance(r)

        if destination_token != None:
            tx['destination_token_symbol'] = destination_token.symbol
            o = erc20_c.balance_of(tx['destination_token'], tx['recipient'], sender_address=self.call_address)
            r = self.rpc.do(o)
            tx['recipient_token_balance'] = erc20_c.parse_balance(r)
            #tx['recipient_token_balance'] = destination_token.function('balanceOf')(tx['recipient']).call()

        # TODO: this can mean either not subitted or culled, need to check other txs with same nonce to determine which
        tx['network_status'] = 'Not in node' 

        r = None
        try:
            o = transaction(tx_hash)
            t = self.proxy_do(chain_spec, o)
            r = t.get()
            if r != None:
                tx['network_status'] = 'Mempool'
        except Exception as e:
            logg.warning('(too permissive exception handler, please fix!) {}'.format(e))

        if r != None:
            try:
                o = receipt(tx_hash)
                t = self.proxy_do(chain_spec, o)
                r = t.get()
                logg.debug('h {} o {}'.format(tx_hash, o))
                if int(strip_0x(r['status'])) == 1:
                    tx['network_status'] = 'Confirmed'
                else:
                    tx['network_status'] = 'Reverted'
                tx['network_block_number'] = r.blockNumber
                tx['network_tx_index'] = r.transactionIndex
                if tx['block_number'] == None:
                    problems.append('Queue is missing block number {} for mined tx'.format(r.blockNumber))
            except Exception as e:
                logg.warning('too permissive exception handler, please fix!')
                pass

        o = balance(tx['sender'])
        t = self.proxy_do(chain_spec, o)
        r = t.get()
        tx['sender_gas_balance'] = r

        o = balance(tx['recipient'])
        t = self.proxy_do(chain_spec, o)
        r = t.get()
        tx['recipient_gas_balance'] = r

        tx_unpacked = unpack(bytes.fromhex(strip_0x(tx['signed_tx'])), chain_spec)
        tx['gas_price'] = tx_unpacked['gasPrice']
        tx['gas_limit'] = tx_unpacked['gas']
        tx['data'] = tx_unpacked['data']

        s = celery.signature(
            'cic_eth.queue.state.get_state_log',
            [
                chain_spec.asdict(),
                tx_hash,
                ],
            queue=self.queue,
            )
        t = s.apply_async()
        tx['status_log'] = t.get()

        if len(problems) > 0:
            sys.stderr.write('\n')
            for p in problems:
                sys.stderr.write('!!!{}\n'.format(p))

        if renderer == None:
            return tx

        r = renderer(tx)
        w.write(r + '\n')
        return None
