# standard imports
import datetime

# third-party imports
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method

# local imports
from cic_eth.db.models.base import SessionBase


class BlockchainSync(SessionBase):
    """Syncer control backend.

    :param chain: Chain spec string representation
    :type chain: str
    :param block_start: Block number to start sync from
    :type block_start: number
    :param tx_start: Block transaction number to start sync from
    :type tx_start: number
    :param block_target: Block number to sync until, inclusive
    :type block_target: number
    """
    __tablename__ = 'blockchain_sync'

    blockchain = Column(String)
    block_start = Column(Integer)
    tx_start = Column(Integer)
    block_cursor = Column(Integer)
    tx_cursor = Column(Integer)
    block_target = Column(Integer)
    date_created = Column(DateTime, default=datetime.datetime.utcnow)
    date_updated = Column(DateTime)


    @staticmethod
    def first(chain, session=None):
        """Check if a sync session for the specified chain already exists.

        :param chain: Chain spec string representation
        :type chain: str
        :param session: Session to use. If not specified, a separate session will be created for this method only.
        :type session: SqlAlchemy Session
        :returns: True if sync record found
        :rtype: bool
        """
        local_session = False
        if session == None:
            session = SessionBase.create_session()
            local_session = True
        q = session.query(BlockchainSync.id)
        q = q.filter(BlockchainSync.blockchain==chain)
        o = q.first()
        if local_session:
            session.close()
        return o == None


    @staticmethod
    def get_last_live_height(current, session=None):
        """Get the most recent open-ended ("live") syncer record.

        :param current: Current block number
        :type current: number
        :param session: Session to use. If not specified, a separate session will be created for this method only.
        :type session: SqlAlchemy Session
        :returns: Block and transaction number, respectively
        :rtype: tuple
        """
        local_session = False
        if session == None:
            session = SessionBase.create_session()
            local_session = True
        q = session.query(BlockchainSync)
        q = q.filter(BlockchainSync.block_target==None)
        q = q.order_by(BlockchainSync.date_created.desc())
        o = q.first()
        if local_session:
            session.close()

        if o == None:
            return (0, 0)

        return (o.block_cursor, o.tx_cursor)


    @staticmethod
    def get_unsynced(session=None):
        """Get previous bounded sync sessions that did not complete.

        :param session: Session to use. If not specified, a separate session will be created for this method only.
        :type session: SqlAlchemy Session
        :returns: Syncer database ids
        :rtype: tuple, where first element is id
        """
        unsynced = []
        local_session = False
        if session == None:
            session = SessionBase.create_session()
            local_session = True
        q = session.query(BlockchainSync.id)
        q = q.filter(BlockchainSync.block_target!=None)
        q = q.filter(BlockchainSync.block_cursor<BlockchainSync.block_target)
        q = q.order_by(BlockchainSync.date_created.asc())
        for u in q.all():
            unsynced.append(u[0])
        if local_session:
            session.close()

        return unsynced


    def set(self, block_height, tx_height):
        """Set the height of the syncer instance.

        Only manipulates object, does not transaction or commit to backend.

        :param block_height: Block number
        :type block_height: number
        :param tx_height: Block transaction number
        :type tx_height: number
        """
        self.block_cursor = block_height
        self.tx_cursor = tx_height


    def cursor(self):
        """Get current state of cursor from cached instance.

        :returns: Block and transaction height, respectively
        :rtype: tuple
        """
        return (self.block_cursor, self.tx_cursor)


    def start(self):
        """Get sync block start position from cached instance.

        :returns: Block and transaction height, respectively
        :rtype: tuple
        """
        return (self.block_start, self.tx_start)


    def target(self):
        """Get sync block upper bound from cached instance.

        :returns: Block number
        :rtype: number, or None if sync is open-ended
        """
        return self.block_target


    def chain(self):
        """Get chain the cached instance represents.
        """
        return self.blockchain


    def __init__(self, chain, block_start, tx_start, block_target=None):
        self.blockchain = chain
        self.block_start = block_start
        self.tx_start = tx_start
        self.block_cursor = block_start
        self.tx_cursor = tx_start
        self.block_target = block_target
        self.date_created = datetime.datetime.utcnow()
        self.date_modified = datetime.datetime.utcnow()
