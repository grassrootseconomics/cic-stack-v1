# standard imports
import os
import sys
import logging
import time
import argparse

# third-party imports
import confini
import celery

# local imports
import cic_eth
from cic_eth import db
from cic_eth import eth
from cic_eth.eth.token import transfer

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

app = celery.Celery(backend='redis://', broker='redis://')

if __name__ == '__main__':
     
    config_dir = os.path.join('/etc/cic-eth/watcher')

    argparser = argparse.ArgumentParser(description='daemon that monitors transactions in new blocks')
    argparser.add_argument('-c', type=str, default=config_dir, help='config root to use')
    argparser.add_argument('-v', help='be verbose', action='store_true')
    argparser.add_argument('-vv', help='be more verbose', action='store_true')
    args = argparser.parse_args(sys.argv[1:])

    config_dir = os.path.join(args.c)
    os.makedirs(config_dir, 0o777, True)

    if args.v == True:
        logging.getLogger().setLevel(logging.INFO)
    elif args.vv == True:
        logging.getLogger().setLevel(logging.DEBUG)

    config = confini.Config(config_dir)
    config.process()
    logg.debug('config loaded from {}'.format(config_dir))

    token_address = '0x528c3E8B3e6dC646530440D88F83da0e45DaC25b' 
    #sender = '0xa2e85B7F1d61522A88f446C52D09F724C807d7ad'
    sender = '0xc14958CD9A605AB0d9A36850362AaD2b9D42DF97'
    recipient = '0xe3C4db5947409Aff0FF8D643047EA41515cA4B8e'

    transfer.delay(
            [{
                'address': token_address
                }],
            sender,
            recipient,
            1000000000000000000000,
            )
