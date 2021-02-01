# standard imports
import logging

# third-party imports
import web3
import celery
from erc20_approval_escrow import TransferApproval
from cic_registry import CICRegistry
from cic_registry.chain import ChainSpec

# local imports
from cic_eth.db.models.tx import TxCache
from cic_eth.db.models.base import SessionBase
from cic_eth.eth import RpcClient
from cic_eth.eth.factory import TxFactory
from cic_eth.eth.task import sign_and_register_tx
from cic_eth.eth.util import unpack_signed_raw_tx
from cic_eth.eth.task import create_check_gas_and_send_task
from cic_eth.error import TokenCountError

celery_app = celery.current_app
logg = logging.getLogger()

contract_function_signatures = {
        'request': 'b0addede',
        }


class TransferRequestTxFactory(TxFactory):
    """Factory for creating Transfer request transactions using the TransferApproval contract backend
    """
    def request(
            self,
            token_address,
            beneficiary_address,
            amount,
            chain_spec,
            ):
        """Create a new TransferApproval.request transaction

        :param token_address: Token to create transfer request for
        :type token_address: str, 0x-hex
        :param beneficiary_address: Beneficiary of token transfer
        :type beneficiary_address: str, 0x-hex
        :param amount: Amount of tokens to transfer
        :type amount: number
        :param chain_spec: Chain spec
        :type chain_spec: cic_registry.chain.ChainSpec
        :returns: Transaction in standard Ethereum format
        :rtype: dict
        """
        transfer_approval = CICRegistry.get_contract(chain_spec, 'TransferApproval', 'TransferAuthorization')
        fn = transfer_approval.function('createRequest')
        tx_approval_buildable = fn(beneficiary_address, token_address, amount)
        transfer_approval_gas = transfer_approval.gas('createRequest')

        tx_approval = tx_approval_buildable.buildTransaction({
            'from': self.address,
            'gas': transfer_approval_gas,
            'gasPrice': self.gas_price,
            'chainId': chain_spec.chain_id(),
            'nonce': self.next_nonce(),
            })
        return tx_approval


def unpack_transfer_approval_request(data):
    """Verifies that a transaction is an "TransferApproval.request" transaction, and extracts call parameters from it.

    :param data: Raw input data from Ethereum transaction.
    :type data: str, 0x-hex
    :raises ValueError: Function signature does not match AccountRegister.add
    :returns: Parsed parameters
    :rtype: dict
    """
    f = data[2:10]
    if f != contract_function_signatures['request']:
        raise ValueError('Invalid transfer request data ({})'.format(f))

    d = data[10:]
    return {
        'to': web3.Web3.toChecksumAddress('0x' + d[64-40:64]),
        'token': web3.Web3.toChecksumAddress('0x' + d[128-40:128]),
        'amount': int(d[128:], 16)
        }


@celery_app.task(bind=True)
def transfer_approval_request(self, tokens, holder_address, receiver_address, value, chain_str):
    """Creates a new transfer approval

    :param tokens: Token to generate transfer request for
    :type tokens: list with single token spec as dict
    :param holder_address: Address to generate transfer on behalf of
    :type holder_address: str, 0x-hex
    :param receiver_address: Address to transfser tokens to
    :type receiver_address: str, 0x-hex
    :param value: Amount of tokens to transfer
    :type value: number
    :param chain_spec: Chain spec string representation
    :type chain_spec: str
    :raises cic_eth.error.TokenCountError: More than one token in tokens argument
    :returns: Raw signed transaction
    :rtype: list with transaction as only element
    """

    if len(tokens) != 1:
        raise TokenCountError

    chain_spec = ChainSpec.from_chain_str(chain_str)

    queue = self.request.delivery_info['routing_key']

    t = tokens[0]

    c = RpcClient(holder_address)

    txf = TransferRequestTxFactory(holder_address, c)

    tx_transfer = txf.request(t['address'], receiver_address, value, chain_spec)
    (tx_hash_hex, tx_signed_raw_hex) = sign_and_register_tx(tx_transfer, chain_str, queue, 'cic_eth.eth.request.otx_cache_transfer_approval_request')

    gas_budget = tx_transfer['gas'] * tx_transfer['gasPrice']

    s = create_check_gas_and_send_task(
             [tx_signed_raw_hex],
             chain_str,
             holder_address,
             gas_budget,
             [tx_hash_hex],
             queue,
            )
    s.apply_async()
    return [tx_signed_raw_hex]


@celery_app.task()
def otx_cache_transfer_approval_request(
        tx_hash_hex,
        tx_signed_raw_hex,
        chain_str,
        ):
    """Generates and commits transaction cache metadata for an TransferApproval.request transaction

    :param tx_hash_hex: Transaction hash
    :type tx_hash_hex: str, 0x-hex
    :param tx_signed_raw_hex: Raw signed transaction
    :type tx_signed_raw_hex: str, 0x-hex
    :param chain_str: Chain spec string representation
    :type chain_str: str
    :returns: Transaction hash and id of cache element in storage backend, respectively
    :rtype: tuple
    """
    chain_spec = ChainSpec.from_chain_str(chain_str)
    tx_signed_raw_bytes = bytes.fromhex(tx_signed_raw_hex[2:])
    tx = unpack_signed_raw_tx(tx_signed_raw_bytes, chain_spec.chain_id())
    logg.debug('in otx acche transfer approval request')
    (txc, cache_id) = cache_transfer_approval_request_data(tx_hash_hex, tx)
    return txc


@celery_app.task()
def cache_transfer_approval_request_data(
    tx_hash_hex,
    tx,
        ):
    """Helper function for otx_cache_transfer_approval_request

    :param tx_hash_hex: Transaction hash
    :type tx_hash_hex: str, 0x-hex
    :param tx: Signed raw transaction
    :type tx: str, 0x-hex
    :returns: Transaction hash and id of cache element in storage backend, respectively
    :rtype: tuple
    """
    tx_data = unpack_transfer_approval_request(tx['data'])
    logg.debug('tx approval request data {}'.format(tx_data))
    logg.debug('tx approval request {}'.format(tx))

    session = SessionBase.create_session()
    tx_cache = TxCache(
        tx_hash_hex,
        tx['from'],
        tx_data['to'],
        tx_data['token'],
        tx_data['token'],
        tx_data['amount'],
        tx_data['amount'],
            )
    session.add(tx_cache)
    session.commit()
    cache_id = tx_cache.id
    session.close()
    return (tx_hash_hex, cache_id)
