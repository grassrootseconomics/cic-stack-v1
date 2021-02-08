import { v4 as uuidv4 } from 'uuid';
import { Syncable } from './sync';
import { Store } from './store';
import { PubSub } from './transport';

function toIndexKey(id:string):string {
	const d = Date.now();
	return d + '_' + id + '_' + uuidv4();
}

const _re_indexKey = /^\d+_(.+)_[-\d\w]+$/;
function fromIndexKey(s:string):string {
	const m = s.match(_re_indexKey);
	if (m === null) {
		throw 'Invalid index key';
	}
	return m[1];
}

class Dispatcher {

	idx:		Array<string>
	syncer:		PubSub
	store:		Store

	constructor(store:Store, syncer:PubSub) {
		this.idx = new Array<string>()
		this.syncer = syncer;
		this.store = store;
	}

	public isDirty(): boolean {
		return this.idx.length > 0;
	}

	public add(id:string, item:Syncable): string {
		const v = item.toJSON();
		const k = toIndexKey(id);
		this.store.put(k, v, true);
		localStorage.setItem(k, v);
		this.idx.push(k);
		return k;
	}

	public sync(offset:number): number {
		let i = 0;
		this.idx.forEach((k) => {
			const v = localStorage.getItem(k);
			const k_id = fromIndexKey(k);
			this.syncer.pub(v); // this must block until guaranteed delivery
			localStorage.removeItem(k);
			i++;
		});
		return i;
	}
}

export { Dispatcher, toIndexKey, fromIndexKey }
