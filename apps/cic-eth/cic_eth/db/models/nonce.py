# standard imports
import logging
import datetime

# third-party imports
from sqlalchemy import Column, String, Integer, DateTime

# local imports
from .base import SessionBase
from cic_eth.error import (
        InitializationError,
        IntegrityError,
        )

logg = logging.getLogger(__name__)


class Nonce(SessionBase):
    """Provides thread-safe nonce increments.
    """
    __tablename__ = 'nonce'

    nonce = Column(Integer)
    address_hex = Column(String(40))


    @staticmethod
    def get(address, session=None):
        session = SessionBase.bind_session(session)

        q = session.query(Nonce)
        q = q.filter(Nonce.address_hex==address)
        nonce = q.first()

        nonce_value = None
        if nonce != None:
            nonce_value = nonce.nonce;

        SessionBase.release_session(session)

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
    def __inc(conn, address):
        #conn.execute("UPDATE nonce set nonce = nonce + 1 WHERE address_hex = '{}'".format(address))
        q = conn.query(Nonce)
        q = q.filter(Nonce.address_hex==address)
        q = q.with_for_update()
        o = q.first()
        nonce =  o.nonce
        o.nonce += 1
        conn.add(o)
        conn.flush()
        return nonce


    @staticmethod
    def __init(conn, address, nonce):
        conn.execute("INSERT INTO nonce (nonce, address_hex) VALUES ({}, '{}')".format(nonce, address))


    @staticmethod
    def init(address, nonce=0, session=None):
        session = SessionBase.bind_session(session)

        q = session.query(Nonce)
        q = q.filter(Nonce.address_hex==address)
        o = q.first()
        if o != None:
            session.flush()
            raise InitializationError('nonce on {} already exists ({})'.format(address, o.nonce))
        session.flush()
        Nonce.__init(session, address, nonce)

        SessionBase.release_session(session)


    # TODO: Incrementing nonce MUST be done by separate tasks.
    @staticmethod
    def next(address, initial_if_not_exists=0, session=None):
        """Generate next nonce for the given address.

        If there is no previous nonce record for the address, the nonce may be initialized to a specified value, or 0 if no value has been given.

        :param address: Associate Ethereum address 
        :type address: str, 0x-hex
        :param initial_if_not_exists: Initial nonce value to set if no record exists
        :type initial_if_not_exists: number
        :returns: Nonce
        :rtype: number
        """
        session = SessionBase.bind_session(session)
        
        #session.begin_nested()
        #conn = Nonce.engine.connect()
        #if Nonce.transactional:
        #    conn.execute('BEGIN')
        #    conn.execute('LOCK TABLE nonce IN SHARE ROW EXCLUSIVE MODE')
        #    logg.debug('locking nonce table for address {}'.format(address))
        #nonce = Nonce.__get(conn, address)
        nonce = Nonce.__get(session, address)
        logg.debug('get nonce {} for address {}'.format(nonce, address))
        if nonce == None:
            nonce = initial_if_not_exists
            logg.debug('setting default nonce to {} for address {}'.format(nonce, address))
            #Nonce.__init(conn, address, nonce)
            Nonce.__init(session, address, nonce)
        #Nonce.__set(conn, address, nonce+1)
        nonce = Nonce.__inc(session, address)
        #if Nonce.transactional:
            #conn.execute('COMMIT')
        #    logg.debug('unlocking nonce table for address {}'.format(address))
        #conn.close()
        #session.commit()

        SessionBase.release_session(session)
        return nonce


class NonceReservation(SessionBase):

    __tablename__ = 'nonce_task_reservation'

    address_hex = Column(String(42))
    nonce = Column(Integer)
    key = Column(String)
    date_created = Column(DateTime, default=datetime.datetime.utcnow)


    @staticmethod
    def peek(address, key, session=None):
        session = SessionBase.bind_session(session)

        q = session.query(NonceReservation)
        q = q.filter(NonceReservation.key==key)
        q = q.filter(NonceReservation.address_hex==address)
        o = q.first()

        r = None
        if o != None:
            r = (o.key, o.nonce)

        session.flush()

        SessionBase.release_session(session)

        return r


    @staticmethod
    def release(address, key, session=None):

        session = SessionBase.bind_session(session)

        o = NonceReservation.peek(address, key, session=session)

        if o == None:
            SessionBase.release_session(session)
            raise IntegrityError('"release" called on key {} address {} which does not exists'.format(key, address))

        q = session.query(NonceReservation)
        q = q.filter(NonceReservation.key==key)
        q = q.filter(NonceReservation.address_hex==address)
        o = q.first()
        r = (o.key, o.nonce)

        session.delete(o)
        session.flush()

        SessionBase.release_session(session)

        return r


    @staticmethod
    def next(address, key, session=None):
        session = SessionBase.bind_session(session)

        o = NonceReservation.peek(address, key, session)
        if o != None:
            raise IntegrityError('"next" called on nonce for key {} address {} during active key {}'.format(key, address, o[0]))

        nonce = Nonce.next(address, session=session)

        o = NonceReservation()
        o.nonce = nonce
        o.key = key
        o.address_hex = address
        session.add(o)
        r = (key, nonce)
       
        SessionBase.release_session(session)

        return r
