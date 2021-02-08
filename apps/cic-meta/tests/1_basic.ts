import * as Automerge from 'automerge';
import assert = require('assert');

import { Dispatcher, toIndexKey, fromIndexKey } from '../src/dispatch';
import { User } from '../src/assets/user';
import { Syncable, ArgPair } from '../src/sync';

import { MockSigner, MockStore } from './mock';

describe('basic', () => {

	it('store', () => {
		const store = new MockStore('s');
		assert.equal(store.name, 's');

		const mockSigner = new MockSigner();
		const v = new Syncable('foo', {baz: 42});
		v.setSigner(mockSigner);
		store.put('foo', v);
		const one = store.get('foo').toJSON();
		const vv = new Syncable('bar', {baz: 666});
		vv.setSigner(mockSigner);
		assert.throws(() => {
			store.put('foo', vv)
		});
		store.put('foo', vv, true);
		const other = store.get('foo').toJSON();
		assert.notEqual(one, other);
		store.delete('foo');
		assert.equal(store.get('foo'), undefined);
	});

	it('add_doc_to_dispatcher', () => {
		const store = new MockStore('s');
		//const syncer = new MockSyncer();
		const dispatcher = new Dispatcher(store, undefined);
		const user = new User('foo'); 
		dispatcher.add(user.id, user);
		assert(dispatcher.isDirty());
	});

	it('dispatch_keyindex', () => {
		const s = 'foo';
		const k = toIndexKey(s);
		const v = fromIndexKey(k);
		assert.equal(s, v);
	});


});
