import sys
import os
import json
import logging
from urllib.request import Request, urlopen

import gnupg

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

host = os.environ.get('CIC_META_URL', 'http://localhost:63380')

if len(sys.argv) < 2:
    sys.stderr.write('Usage: {} <path-to-gpg-private-key>\n'.format(sys.argv[0]))
    sys.exit(1)


# Import PGP key used to sign the data submission
gpg = gnupg.GPG(gnupghome='/tmp/.gpg')
f = open(sys.argv[1], 'r')
key_data = f.read()
f.close()

gpg.import_keys(key_data)
gpgk = gpg.list_keys()
algo = gpgk[0]['algo']
logg.info('using signing key {} algo {}'.format(gpgk[0]['keyid'], algo))


def main():

    # Random key to associate with value
    # (typically this is some deterministic identifier like sha256(<ethaddress>:cic-person)
    k = os.urandom(32).hex()
    url = os.path.join(host, k)

    # Headers required for server-assisted merge operations
    headers = {
        'X-CIC-AUTOMERGE': 'server',
        'Content-Type': 'application/json',
            }

    # Data to merge
    data_dict = {
        'foo': 'bar',
        'xyzzy': 42,
            }

    # Send request to server to get initial automerge object and signing material
    # Server will reply with current state of object merged with ours, but (obviously)
    # still without a signature.
    data = json.dumps(data_dict).encode('utf-8')
    req = Request(url, headers=headers, data=data, method='POST')
    rs = urlopen(req)
    logg.info('get sign material response status: {}'.format(rs.status))
    if rs.status != 200:
        raise RuntimeError('request failed: {}'.format(rs.reason))


    # Sign the provided digest
    data = rs.read()
    e = json.loads(data)
    sig = gpg.sign(e['digest'], passphrase='ge', keyid=gpgk[0]['keyid'])

    # Format data for the content storage request
    data = {
            'm': data.decode('utf-8'),
            's': {
        'engine': 'pgp',
        'algo': algo,
        'data': str(sig),
        'digest': e['digest'],
            },
            }

    # Send storage request to server
    data = json.dumps(data).encode('utf-8')
    req = Request(url, headers=headers, data=data, method='PUT')
    rs = urlopen(req)

    logg.info('signed content submissionstatus: {}'.format(rs.status))
    if rs.status != 200:
        raise RuntimeError('request failed: {}'.format(rs.reason))


    # Get the latest stored version of the data (without the merge graph)
    req = Request(url, method='GET')
    rs = urlopen(req)
    logg.info('get latest data status: {}'.format(rs.status))
    if rs.status != 200:
        raise RuntimeError('request failed: {}'.format(rs.reason))

    print(rs.read().decode('utf-8'))


if __name__ == '__main__':
    main()
