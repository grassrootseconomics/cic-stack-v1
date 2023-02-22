#!python3

# SPDX-License-Identifier: GPL-3.0-or-later

# standard imports
import os
import json
import argparse
import logging
import sys
import re
import datetime

# external imports
from chainlib.chain import ChainSpec
from chainlib.eth.connection import EthHTTPConnection
from chainqueue.enum import (
    StatusEnum,
    StatusBits,
    status_str,
    )
from chainlib.eth.tx import receipt
from potaahto.symbols import snake_and_camel

# local imports
import cic_eth.cli
from cic_eth.cli.audit import AuditSession


logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()
logging.getLogger('chainlib').setLevel(logging.WARNING)

default_format = 'terminal'

extra_args = {
    'f': '_FORMAT',
    'include': '_INCLUDE',
    'exclude': '_EXCLUDE',
    'after': '_AFTER',
    'o': '_OUTPUT_DIR',
}

arg_flags = cic_eth.cli.argflag_std_base
local_arg_flags = cic_eth.cli.argflag_local_taskcallback
argparser = cic_eth.cli.ArgumentParser(arg_flags, description="")
argparser.add_argument('-f', '--format', dest='f', default=default_format, type=str, help='Output format')
argparser.add_argument('--include', dest='include', action='append', type=str, help='Include audit module')
argparser.add_argument('--exclude', dest='exclude', action='append', type=str, help='Exclude audit module')
argparser.add_argument('-o', '--output-dir', dest='o', type=str, help='Output transaction hashes to this directory')
argparser.add_argument('--after', type=int, help='Only match transactions after this timetstamp')
argparser.process_local_flags(local_arg_flags)
args = argparser.parse_args()

config = cic_eth.cli.Config.from_args(args, arg_flags, local_arg_flags, extra_args=extra_args)

chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))

# set up rpc
rpc = cic_eth.cli.RPC.from_config(config) #, use_signer=True)
conn = rpc.get_default()

def process_otx(session, chain_spec, rpc=None, commit=False, w=sys.stdout, extra_args=None):
    filter_status = StatusBits.FINAL
    s = 'select tx_hash, date_updated, id, status from otx where status & {} = 0'.format(filter_status)
    if config.get('_AFTER') != None:
        s += ' and date_created >= \'{}\''.format(config.get('_AFTER'))
    s += ' order by otx.date_updated asc'
    r = session.execute(s)
    for v in r.fetchall():
        logg.debug('processing {} last updated {}'.format(v[0], v[1]))
        o = receipt(v[0])
        rr = conn.do(o)
        if rr != None:
            rr = snake_and_camel(rr)
            logg.info('rr {}'.format(rr))
            block_number = int(rr['block_number'], 16)
            tx_index = int(rr['transaction_index'], 16)
            status = StatusBits.FINAL | StatusBits.MANUAL
            if rr['status'] == 0:
                status = StatusBits.NETWORK_ERROR
            status_result = v[3] | status
            logg.info('setting final bit (result {}) on tx {} mined in block {} index {}'.format(status_str(status_result), v[0], block_number, tx_index))
            session.execute('update otx set status = {}, block = {} where tx_hash = \'{}\''.format(status, block_number, v[0]))
            session.execute('update tx_cache set tx_index = {} where otx_id = {}'.format(tx_index, v[2]))
            session.execute('insert into otx_state_log (otx_id, date, status) values ({}, \'{}\', {})'.format(v[2], datetime.datetime.utcnow(), status)) 
            session.commit()



def main():
    after = config.get('_AFTER')
    if after != None:
        after = datetime.datetime.fromtimestamp(after)
    config.add(after, '_AFTER', True)

    o = AuditSession(config, chain_spec)
    g = globals()
    o.register('otx', process_otx)
    o.run()


if __name__ == '__main__':
    main()
