import assert = require('assert');
import pgp = require('openpgp');
import crypto  = require('crypto');

import { Syncable, ArgPair } from '../src/sync';

import { MockKeyStore, MockSignable } from './mock';

import { PGPSigner } from '../src/auth';


describe('auth', async () => {
	await it('digest', async () => {
		const opts = {
			userIds: [
				{
					name: 'John Marston',
					email: 'red@dead.com',
				},
			],
			numBits: 2048,
			passphrase: 'foo',
		};
		const pkgen = await pgp.generateKey(opts);
		const pka = pkgen.privateKeyArmored;
		const pks = await pgp.key.readArmored(pka);
		await pks.keys[0].decrypt('foo');
		const pubka = pkgen.publicKeyArmored;
		const pubks = await pgp.key.readArmored(pubka);
		const keyStore = new MockKeyStore(pks.keys[0], pubks.keys);
		const s = new PGPSigner(keyStore);

		const message = await pgp.cleartext.fromText('foo');
		s.onverify = (ok) => {
			assert(ok);
		}
		s.onsign = (signature) => {
			s.onverify((v) => {
				console.log('bar', v);
			});
			s.verify('foo', signature);
		}
		
		await s.sign('foo');
	});
});	
