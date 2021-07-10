# standard imports
import logging
import json
import re
import base64

# external imports
from hexathon import add_0x

# local imports
from cic_cache.cache import (
        BloomCache,
        DataCache,
    )

logg = logging.getLogger(__name__)
#logg = logging.getLogger()

re_transactions_all_bloom = r'/tx/(\d+)?/?(\d+)/?'
re_transactions_account_bloom = r'/tx/user/((0x)?[a-fA-F0-9]+)(/(\d+)(/(\d+))?)?/?'
re_transactions_all_data = r'/txa/(\d+)?/?(\d+)/?'

DEFAULT_LIMIT = 100


def process_transactions_account_bloom(session, env):
    r = re.match(re_transactions_account_bloom, env.get('PATH_INFO'))
    if not r:
        return None

    address = r[1]
    if r[2] == None:
        address = add_0x(address)
    offset = 0
    if r.lastindex > 2:
        offset = r[4]
    limit = DEFAULT_LIMIT
    if r.lastindex > 4:
        limit = r[6]

    c = BloomCache(session)
    (lowest_block, highest_block, bloom_filter_block, bloom_filter_tx) = c.load_transactions_account(address, offset, limit)

    o = {
        'alg': 'sha256',
        'low': lowest_block,
        'high': highest_block,
        'block_filter': base64.b64encode(bloom_filter_block).decode('utf-8'),
        'blocktx_filter': base64.b64encode(bloom_filter_tx).decode('utf-8'),
        'filter_rounds': 3,
            }

    j = json.dumps(o)

    return ('application/json', j.encode('utf-8'),)


def process_transactions_all_bloom(session, env):
    r = re.match(re_transactions_all_bloom, env.get('PATH_INFO'))
    if not r:
        return None

    offset = DEFAULT_LIMIT
    if r.lastindex > 0:
        offset = r[1]
    limit = 0
    if r.lastindex > 1:
        limit = r[2]

    c = BloomCache(session)
    (lowest_block, highest_block, bloom_filter_block, bloom_filter_tx) = c.load_transactions(offset, limit)

    o = {
        'alg': 'sha256',
        'low': lowest_block,
        'high': highest_block,
        'block_filter': base64.b64encode(bloom_filter_block).decode('utf-8'),
        'blocktx_filter': base64.b64encode(bloom_filter_tx).decode('utf-8'),
        'filter_rounds': 3,
            }

    j = json.dumps(o)

    return ('application/json', j.encode('utf-8'),)


def process_transactions_all_data(session, env):
    r = re.match(re_transactions_all_data, env.get('PATH_INFO'))
    if not r:
        return None
    if env.get('HTTP_X_CIC_CACHE_MODE') != 'all':
        return None

    offset = r[1]
    end = r[2]
    if int(r[2]) < int(r[1]):
        raise ValueError('cart before the horse, dude')

    c = DataCache(session)
    (lowest_block, highest_block, tx_cache) = c.load_transactions_with_data(offset, end)

    for r in tx_cache:
        r['date_block'] = r['date_block'].timestamp()

    o = {
        'low': lowest_block,
        'high': highest_block,
        'data': tx_cache,
    }

    
    j = json.dumps(o)

    return ('application/json', j.encode('utf-8'),)
