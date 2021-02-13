# standard imports
import enum


@enum.unique
class StatusBits(enum.IntEnum):
    QUEUED = 0x01
    IN_NETWORK = 0x08
   
    DEFERRED = 0x10
    GAS_ISSUES = 0x20

    LOCAL_ERROR = 0x100
    NODE_ERROR = 0x200
    NETWORK_ERROR = 0x400
    UNKNOWN_ERROR = 0x800

    FINAL = 0x1000
    OBSOLETE = 0x2000
    MANUAL = 0x8000


@enum.unique
class StatusEnum(enum.IntEnum):
    """

    - Inactive, not finalized. (<0)
        * PENDING: The initial state of a newly added transaction record. No action has been performed on this transaction yet.
        * SENDFAIL: The transaction was not received by the node.
        * RETRY: The transaction is queued for a new send attempt after previously failing.
        * READYSEND: The transaction is queued for its first send attempt
        * OBSOLETED: A new transaction with the same nonce and higher gas has been sent to network.
        * WAITFORGAS: The transaction is on hold pending gas funding.
    - Active state: (==0)
        * SENT: The transaction has been sent to the mempool.
    - Inactive, finalized. (>0)
        * FUBAR: Unknown error occurred and transaction is abandoned. Manual intervention needed.
        * CANCELLED: The transaction was sent, but was not mined and has disappered from the mempool. This usually follows a transaction being obsoleted.
        * OVERRIDDEN: Transaction has been manually overriden.
        * REJECTED: The transaction was rejected by the node.
        * REVERTED: The transaction was mined, but exception occurred during EVM execution. (Block number will be set)
        * SUCCESS: THe transaction was successfully mined. (Block number will be set)

    """
    PENDING = 0

    SENDFAIL = StatusBits.DEFERRED | StatusBits.LOCAL_ERROR
    RETRY = StatusBits.QUEUED | StatusBits.DEFERRED 
    READYSEND = StatusBits.QUEUED

    OBSOLETED = StatusBits.OBSOLETE | StatusBits.IN_NETWORK

    WAITFORGAS = StatusBits.GAS_ISSUES

    SENT = StatusBits.IN_NETWORK
    FUBAR = StatusBits.FINAL | StatusBits.UNKNOWN_ERROR
    CANCELLED = StatusBits.IN_NETWORK | StatusBits.FINAL | StatusBits.OBSOLETE
    OVERRIDDEN = StatusBits.FINAL | StatusBits.OBSOLETE | StatusBits.MANUAL

    REJECTED = StatusBits.NODE_ERROR | StatusBits.FINAL
    REVERTED = StatusBits.IN_NETWORK | StatusBits.FINAL | StatusBits.NETWORK_ERROR
    SUCCESS = StatusBits.IN_NETWORK | StatusBits.FINAL 


@enum.unique
class LockEnum(enum.IntEnum):
    """
    STICKY: When set, reset is not possible
    CREATE: Disable creation of accounts
    SEND: Disable sending to network
    QUEUE: Disable queueing new or modified transactions
    """
    STICKY=1
    CREATE=2
    SEND=4
    QUEUE=8
    QUERY=16
    ALL=int(0xfffffffffffffffe)


def status_str(v, bits_only=False):
    s = ''
    if not bits_only:
        try:
            s = StatusEnum(v).name
            return s
        except ValueError:
            pass

    for i in range(16):
        b = (1 << i)
        if (b & 0xffff) & v:
            n = StatusBits(b).name
            if len(s) > 0:
                s += ','
            s += n
    if not bits_only:
        s += '*'
    return s


def all_errors():
    return StatusBits.LOCAL_ERROR | StatusBits.NODE_ERROR | StatusBits.NETWORK_ERROR | StatusBits.UNKNOWN_ERROR


def is_error_status(v):
    return bool(v & all_errors())


def is_alive(v):
    return bool(v & (StatusBits.FINAL | StatusBits.OBSOLETE) == 0)


