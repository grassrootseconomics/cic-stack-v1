"""Ethereum batch functions and utilities

.. moduleauthor:: Louis Holbrook <dev@holbrook.no>

"""
# standard imports
import os

# local imports
from .rpc import RpcClient

registry_extra_identifiers = {
        'Faucet': '0x{:0<64s}'.format(b'Faucet'.hex()),
        'TransferApproval': '0x{:0<64s}'.format(b'TransferApproval'.hex()),
        }

