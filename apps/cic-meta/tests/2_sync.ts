import * as Automerge from 'automerge';
import assert = require('assert');

import * as pgp from 'openpgp';
import * as fs from 'fs';

import { PGPSigner } from '../src/auth';

import { Syncable, ArgPair } from '../src/sync';

import { MockKeyStore, MockSigner } from './mock';


describe('sync', async () => {
	it('sync_merge', () => {
		const mockSigner = new MockSigner();
		const s = new Syncable('foo', {
			bar: 'baz',
		});
		s.setSigner(mockSigner);
		const changePair = new ArgPair('xyzzy', 42);
		s.update([changePair], 'ch-ch-cha-changes');
		assert.equal(s.m.data['xyzzy'], 42)
		assert.equal(s.m.data['bar'], 'baz')
		assert.equal(s.m['id'], 'foo')
		assert.equal(Automerge.getHistory(s.m).length, 2);
	});

	it('sync_serialize', () => {
		const mockSigner = new MockSigner();
		const s = new Syncable('foo', {
			bar: 'baz',
		});
		s.setSigner(mockSigner);
		const j = s.toJSON();
		const ss = Syncable.fromJSON(j);
		assert.equal(ss.m['id'], 'foo');
		assert.equal(ss.m['data']['bar'], 'baz');
		assert.equal(Automerge.getHistory(ss.m).length, 1);
	});

	it('sync_sign_and_wrap', () => {
		const mockSigner = new MockSigner();
		const s = new Syncable('foo', {
			bar: 'baz',
		});
		s.setSigner(mockSigner);
		s.onwrap = (e) => {
			const j = e.toJSON();
			const v = JSON.parse(j);
			assert.deepEqual(v.payload, e.o.payload);

		}
		s.sign();
	});
	it('sync_verify_success', async () => {
		const pksa = fs.readFileSync(__dirname + '/privatekeys.asc');
		const pks = await pgp.key.readArmored(pksa);
		await pks.keys[0].decrypt('merman');
		await pks.keys[1].decrypt('beastman');

		const pubksa = fs.readFileSync(__dirname + '/publickeys.asc');
		const pubks = await pgp.key.readArmored(pubksa);

		const oneStore = new MockKeyStore(pks.keys[0], pubks.keys);
		const twoStore = new MockKeyStore(pks.keys[1], pubks.keys);
		const threeStore = new MockKeyStore(pks.keys[2], [pubks.keys[0], pubks.keys[2]]);

		const oneSigner = new PGPSigner(oneStore);
		const twoSigner = new PGPSigner(twoStore);
		const threeSigner = new PGPSigner(threeStore);

		const x = new Syncable('foo', {
			bar: 'baz',		  
		});
		x.setSigner(oneSigner);

		// TODO: make this look better
		x.onwrap = (e) => {
			let updateData = new ArgPair('bar', 'xyzzy');
			x.update([updateData], 'change one');

			x.onwrap = (e) => {
				x.setSigner(twoSigner);
				updateData = new ArgPair('bar', 42);
				x.update([updateData], 'change two');

				x.onwrap = (e) => {
					const p = e.unwrap();
					p.setSigner(twoSigner);
					p.onauthenticate = (v) => {
						assert(v);
					}
					p.authenticate();
				}

				x.sign();
			};

			x.sign();
		}

		x.sign();

	});

	it('sync_verify_fail', async () => {
		const pksa = fs.readFileSync(__dirname + '/privatekeys.asc');
		const pks = await pgp.key.readArmored(pksa);
		await pks.keys[0].decrypt('merman');
		await pks.keys[1].decrypt('beastman');

		const pubksa = fs.readFileSync(__dirname + '/publickeys.asc');
		const pubks = await pgp.key.readArmored(pubksa);

		const oneStore = new MockKeyStore(pks.keys[0], pubks.keys);
		const twoStore = new MockKeyStore(pks.keys[1], pubks.keys);
		const threeStore = new MockKeyStore(pks.keys[2], [pubks.keys[0], pubks.keys[2]]);

		const oneSigner = new PGPSigner(oneStore);
		const twoSigner = new PGPSigner(twoStore);
		const threeSigner = new PGPSigner(threeStore);

		const x = new Syncable('foo', {
			bar: 'baz',		  
		});
		x.setSigner(oneSigner);

		// TODO: make this look better
		x.onwrap = (e) => {
			let updateData = new ArgPair('bar', 'xyzzy');
			x.update([updateData], 'change one');

			x.onwrap = (e) => {
				x.setSigner(twoSigner);
				updateData = new ArgPair('bar', 42);
				x.update([updateData], 'change two');

				x.onwrap = (e) => {
					const p = e.unwrap();
					p.setSigner(threeSigner);
					p.onauthenticate = (v) => {
						assert(!v);
					}
					p.authenticate();
				}

				x.sign();
			};

			x.sign();
		}

		x.sign();

	});

	xit('sync_verify_shallow_tricked', async () => {
		const pksa = fs.readFileSync(__dirname + '/privatekeys.asc');
		const pks = await pgp.key.readArmored(pksa);
		await pks.keys[0].decrypt('merman');
		await pks.keys[1].decrypt('beastman');

		const pubksa = fs.readFileSync(__dirname + '/publickeys.asc');
		const pubks = await pgp.key.readArmored(pubksa);

		const oneStore = new MockKeyStore(pks.keys[0], pubks.keys);
		const twoStore = new MockKeyStore(pks.keys[1], pubks.keys);
		const threeStore = new MockKeyStore(pks.keys[2], [pubks.keys[0], pubks.keys[2]]);

		const oneSigner = new PGPSigner(oneStore);
		const twoSigner = new PGPSigner(twoStore);
		const threeSigner = new PGPSigner(threeStore);

		const x = new Syncable('foo', {
			bar: 'baz',		  
		});
		x.setSigner(twoSigner);

		// TODO: make this look better
		x.onwrap = (e) => {
			let updateData = new ArgPair('bar', 'xyzzy');
			x.update([updateData], 'change one');

			x.onwrap = (e) => {
				updateData = new ArgPair('bar', 42);
				x.update([updateData], 'change two');
				x.setSigner(oneSigner);

				x.onwrap = (e) => {
					const p = e.unwrap();
					p.setSigner(threeSigner);
					p.onauthenticate = (v) => {
						assert(v);
						p.onauthenticate = (v) => {
							assert(!v);
						}
						p.authenticate(true);
					}
					p.authenticate();
				}

				x.sign();
			};

			x.sign();
		}

		x.sign();

	});
});
