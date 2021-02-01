# third-party imports
from sqlalchemy import Column, Enum, String, Integer
from sqlalchemy.ext.hybrid import hybrid_method

# local imports
from .base import SessionBase
from ..error import UnknownConvertError


class TxConvertTransfer(SessionBase):
    """Table describing a transfer of funds after conversion has been successfully performed.

    :param convert_tx_hash: Transaction hash of convert transaction
    :type convert_tx_hash: str, 0x-hex
    :param recipient_address: Ethereum address of recipient of resulting token balance of conversion
    :type recipient_address: str, 0x-hex
    :param chain_str: Chain spec string representation
    :type chain_str: str
    """
    __tablename__ = 'tx_convert_transfer'

    #approve_tx_hash = Column(String(66))
    convert_tx_hash = Column(String(66))
    transfer_tx_hash = Column(String(66))
    recipient_address = Column(String(42))

    
    @hybrid_method
    def transfer(self, transfer_tx_hash):
        """Persists transaction hash of performed transfer. Setting this ends the lifetime of this record.
        """
        self.transfer_tx_hash = transfer_tx_hash


    @staticmethod
    def get(convert_tx_hash):
        """Retrieves a convert transfer record by conversion transaction hash in a separate session.

        :param convert_tx_hash: Transaction hash of convert transaction
        :type convert_tx_hash: str, 0x-hex
        """
        session = SessionBase.create_session()
        q = session.query(TxConvertTransfer)
        q = q.filter(TxConvertTransfer.convert_tx_hash==convert_tx_hash)
        r = q.first()
        session.close()
        if r == None:
            raise UnknownConvertError(convert_tx_hash)
        return r


    def __init__(self, convert_tx_hash, recipient_address, chain_str):
        self.convert_tx_hash = convert_tx_hash
        self.recipient_address = recipient_address
        self.chain_str = chain_str
