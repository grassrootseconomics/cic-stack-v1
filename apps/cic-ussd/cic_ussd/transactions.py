# standard imports
import decimal
import logging
from datetime import datetime

# third-party imports
from cic_eth.api import Api

# local imports
from cic_ussd.balance import get_balances, get_cached_operational_balance
from cic_ussd.notifications import Notifier
from cic_ussd.phone_number import Support

logg = logging.getLogger()
notifier = Notifier()


def truncate(value: float, decimals: int):
    """This function truncates a value to a specified number of decimals places.
    :param value: The value to be truncated.
    :type value: float
    :param decimals: The number of decimals for the value to be truncated to
    :type decimals: int
    :return: The truncated value.
    :rtype: int
    """
    decimal.getcontext().rounding = decimal.ROUND_DOWN
    contextualized_value = decimal.Decimal(value)
    return round(contextualized_value, decimals)


def from_wei(value: int) -> float:
    """This function converts values in Wei to a token in the cic network.
    :param value: Value in Wei
    :type value: int
    :return: SRF equivalent of value in Wei
    :rtype: float
    """
    value = float(value) / 1e+6
    return truncate(value=value, decimals=2)


def to_wei(value: int) -> int:
    """This functions converts values from a token in the cic network to Wei.
    :param value: Value in SRF
    :type value: int
    :return: Wei equivalent of value in SRF
    :rtype: int
    """
    return int(value * 1e+6)


class OutgoingTransactionProcessor:

    def __init__(self, chain_str: str, from_address: str, to_address: str):
        """
        :param chain_str: The chain name and network id.
        :type chain_str: str
        :param from_address: Ethereum address of the sender
        :type from_address: str, 0x-hex
        :param to_address: Ethereum address of the recipient
        :type to_address: str, 0x-hex
        """
        self.chain_str = chain_str
        self.cic_eth_api = Api(chain_str=chain_str)
        self.from_address = from_address
        self.to_address = to_address

    def process_outgoing_transfer_transaction(self, amount: int, token_symbol: str):
        """This function initiates standard transfers between one account to another
        :param amount: The amount of tokens to be sent
        :type amount: int
        :param token_symbol: ERC20 token symbol of token to send
        :type token_symbol: str
        """
        self.cic_eth_api.transfer(from_address=self.from_address,
                                  to_address=self.to_address,
                                  value=to_wei(value=amount),
                                  token_symbol=token_symbol)
