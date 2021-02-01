# standard imports
import logging

# third-party imports
from sqlalchemy import Column, String, Text
from cic_registry import zero_address

# local imports
from .base import SessionBase

logg = logging.getLogger()


class AccountRole(SessionBase):
    """Key-value store providing plaintext tags for Ethereum addresses.

    Address is initialized to the zero-address

    :param tag: Tag
    :type tag: str
    """
    __tablename__ = 'account_role'

    tag = Column(Text)
    address_hex = Column(String(42))


    @staticmethod
    def get_address(tag):
        """Get Ethereum address matching the given tag

        :param tag: Tag
        :type tag: str
        :returns: Ethereum address, or zero-address if tag does not exist
        :rtype: str, 0x-hex
        """
        role = AccountRole.get_role(tag)
        if role == None:
            return zero_address
        return role.address_hex


    @staticmethod
    def get_role(tag):
        """Get AccountRole model object matching the given tag

        :param tag: Tag
        :type tag: str
        :returns: Role object, if found
        :rtype: cic_eth.db.models.role.AccountRole
        """
        session = AccountRole.create_session()
        role = AccountRole.__get_role(session, tag)
        session.close()
        #return role.address_hex
        return role


    @staticmethod
    def __get_role(session, tag):
        return session.query(AccountRole).filter(AccountRole.tag==tag).first()


    @staticmethod    
    def set(tag, address_hex):
        """Persist a tag to Ethereum address association. 

        This will silently overwrite the existing value.

        :param tag: Tag
        :type tag: str
        :param address_hex: Ethereum address
        :type address_hex: str, 0x-hex
        :returns: Role object
        :rtype: cic_eth.db.models.role.AccountRole
        """
        #session = AccountRole.create_session()
        #role = AccountRole.__get(session, tag)
        role = AccountRole.get_role(tag) #session, tag)
        if role == None:
            role = AccountRole(tag)
        role.address_hex = address_hex
        #session.add(role)
        #session.commit()
        #session.close()
        return role #address_hex


    @staticmethod
    def role_for(address, session=None):
        """Retrieve role for the given address

        :param address: Ethereum address to match role for
        :type address: str, 0x-hex
        :returns: Role tag, or None if no match
        :rtype: str or None
        """
        localsession = session
        if localsession == None:
            localsession = SessionBase.create_session()

        q = localsession.query(AccountRole)
        q = q.filter(AccountRole.address_hex==address)
        role = q.first()
        tag = None
        if role != None:
            tag = role.tag

        if session == None:
            localsession.close()
       
        return tag


    def __init__(self, tag):
        self.tag = tag
        self.address_hex = zero_address
