# standard imports
import logging

# third-party imports
from sqlalchemy import Column, String, Integer

# local imports
from .base import SessionBase

logg = logging.getLogger()


class Nonce(SessionBase):
    """Provides thread-safe nonce increments.
    """
    __tablename__ = 'nonce'

    nonce = Column(Integer)
    address_hex = Column(String(42))


    @staticmethod
    def get(address, session=None):
        localsession = session
        if localsession == None:
            localsession = SessionBase.create_session()


        q = localsession.query(Nonce)
        q = q.filter(Nonce.address_hex==address)
        nonce = q.first()

        nonce_value = None
        if nonce != None:
            nonce_value = nonce.nonce;

        if session == None:
            localsession.close()

        return nonce_value


    @staticmethod
    def __get(conn, address):
        r = conn.execute("SELECT nonce FROM nonce WHERE address_hex = '{}'".format(address))
        nonce = r.fetchone()
        if nonce == None:
            return None
        return nonce[0]


    @staticmethod
    def __set(conn, address, nonce):
        conn.execute("UPDATE nonce set nonce = {} WHERE address_hex = '{}'".format(nonce, address))


    @staticmethod
    def next(address, initial_if_not_exists=0):
        """Generate next nonce for the given address.

        If there is no previous nonce record for the address, the nonce may be initialized to a specified value, or 0 if no value has been given.

        :param address: Associate Ethereum address 
        :type address: str, 0x-hex
        :param initial_if_not_exists: Initial nonce value to set if no record exists
        :type initial_if_not_exists: number
        :returns: Nonce
        :rtype: number
        """
        conn = Nonce.engine.connect()
        if Nonce.transactional:
            conn.execute('BEGIN')
            conn.execute('LOCK TABLE nonce IN SHARE ROW EXCLUSIVE MODE')
        nonce = Nonce.__get(conn, address)
        logg.debug('get nonce {} for address {}'.format(nonce, address))
        if nonce == None:
            nonce = initial_if_not_exists
            conn.execute("INSERT INTO nonce (nonce, address_hex) VALUES ({}, '{}')".format(nonce, address))
            logg.debug('setting default nonce to {} for address {}'.format(nonce, address))
        Nonce.__set(conn, address, nonce+1)
        if Nonce.transactional:
            conn.execute('COMMIT')
        conn.close()
        return nonce


