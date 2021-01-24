#!python3

# Author:	Louis Holbrook <dev@holbrook.no> 0826EDA1702D1E87C6E2875121D2E7BB88C2A746
# SPDX-License-Identifier:	GPL-3.0-or-later
# File-version: 1
# Description: Smoke test for cic-eth create account api

# standard imports
import os
import logging

# third-party imports
import celery
import confini

# platform imports
from cic_eth import Api

script_dir = os.path.dirname(__file__)

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

config_dir = os.environ.get('CONFINI_DIR', '/usr/local/etc/cic/')

config = confini.Config(config_dir)
config.process()

a = Api()
t = a.create_account()
logg.debug('create account task uuid {}'.format(t))
