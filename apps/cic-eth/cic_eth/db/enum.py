# standard imports
import enum

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
    PENDING=-9
    SENDFAIL=-8
    RETRY=-7
    READYSEND=-6
    OBSOLETED=-2
    WAITFORGAS=-1
    SENT=0
    FUBAR=1
    CANCELLED=2
    OVERRIDDEN=3
    REJECTED=7
    REVERTED=8
    SUCCESS=9


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
    ALL=int(0xfffffffffffffffe)
