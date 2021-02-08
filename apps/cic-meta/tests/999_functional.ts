import * as assert from 'assert';
import * as pgp from 'openpgp';

import { Dispatcher } from '../src/dispatch';
import { User } from '../src/assets/user';
import { PGPSigner, KeyStore } from '../src/auth';
import { SubConsumer } from '../src/transport';

import { MockStore, MockPubSub, MockConsumer, MockKeyStore } from './mock';

async function createKeyStore() {
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
	return new MockKeyStore(pks.keys[0], []);
}

describe('fullchain', async () => {
	it('dispatch_and_publish_user', async () => {
		const g = await createKeyStore();
		const n = new PGPSigner(g);
		const u = new User('u1', {});
		u.setSigner(n);
		u.setName('Nico', 'Bellic');
		const s = new MockStore('fooStore');
		const c = new MockConsumer();
		const p = new MockPubSub('fooPubSub', c);
		const d = new Dispatcher(s, p);
		u.onwrap = (e) => {
			d.add(u.id, e);
			d.sync(0);
			assert.equal(p.pubs.length, 1);
		};
		u.sign();
	});
});
