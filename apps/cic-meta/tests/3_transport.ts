import * as assert from 'assert';

import { MockPubSub, MockConsumer } from './mock';

describe('transport', () => {
	it('pub_sub', () => {
		const c = new MockConsumer();
		const ps = new MockPubSub('foo', c);
		ps.pub('foo');	
		ps.pub('bar');
		ps.flush();
		assert.deepEqual(c.omnoms, ['foo', 'bar']);
	});
});
