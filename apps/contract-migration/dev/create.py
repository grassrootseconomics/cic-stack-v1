#!/usr/bin/python
import sys
import os
import logging

import celery
from cic_eth.api import Api
import confini
import argparse

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger('create_account_script')
logging.getLogger('confini').setLevel(logging.WARNING)
logging.getLogger('gnupg').setLevel(logging.WARNING)

config_dir = os.environ.get('CONFINI_DIR', '/usr/local/etc/cic')

argparser = argparse.ArgumentParser()
argparser.add_argument('--no-register', dest='no_register', action='store_true', help='Do not register new account in on-chain accounts index')
argparser.add_argument('-v', action='store_true', help='Be verbose')
argparser.add_argument('-vv', action='store_true', help='Be more verbose')
args = argparser.parse_args()

if args.vv:
    logg.setLevel(logging.DEBUG)
if args.v:
    logg.setLevel(logging.INFO)

config = confini.Config(config_dir, os.environ.get('CONFINI_ENV_PREFIX'))
config.process()

celery_app = celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))

api = Api(config.get('CIC_CHAIN_SPEC'))

registration_account = None
#t = api.create_account(registration_account=registration_account)
if len(sys.argv) > 1:
    registration_account = config.get('DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER', None)

logg.debug('accounts index writer NOT USED {}'.format(registration_account))

register = not args.no_register
logg.debug('register {}'.format(register))
t = api.create_account(register=register)

print(t.get())
