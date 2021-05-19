# standard imports
from enum import IntEnum


class AfricasTalkingStatusCodes(IntEnum):
    PROCESSED = 100
    SENT = 101
    QUEUED = 102
    RISK_HOLD = 401
    INVALID_SENDER_ID = 402
    INVALID_PHONE_NUMBER = 403
    UNSUPPORTED_NUMBER_TYPE = 404
    INSUFFICIENT_BALANCE = 405
    USER_IN_BLACKLIST = 406
    COULD_NOT_ROUTE = 407
    INTERNAL_SERVER_ERROR = 500
    GATEWAY_ERROR = 501
    REJECTED_BY_GATEWAY = 502

