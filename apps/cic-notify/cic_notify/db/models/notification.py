# standard imports
import datetime

# third-party imports
from sqlalchemy import Enum, Column, String, DateTime

# local imports
from .base import SessionBase
from ..enum import NotificationStatusEnum, NotificationTransportEnum


class Notification(SessionBase):
    __tablename__ = 'notification'

    transport = Column(Enum(NotificationTransportEnum))
    status = Column(Enum(NotificationStatusEnum))
    recipient = Column(String)
    message = Column(String)
    created = Column(DateTime, default=datetime.datetime.utcnow)
    updated = Column(DateTime, default=datetime.datetime.utcnow)

    def __init__(self, transport, recipient, message, **kwargs):
        super(Notification, self).__init__(**kwargs)
        self.transport = transport
        self.recipient = recipient
        self.message = message
        self.status = NotificationStatusEnum.UNKNOWN
